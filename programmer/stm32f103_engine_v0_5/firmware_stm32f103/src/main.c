/*
 * SDA555XFL FPI reader for STM32F103C8T6
 * v0.5 — SST39LF/VF010 PROGRAM/RECOVERY ENGINE (COMPILE-LOCKED BY DEFAULT)
 *
 * HSI 8 MHz, USART1 115200 8N1.
 * PA0..PA7 = FPI P0 bus
 * PA8       = RESET#
 * PA9       = USART1 TX
 * PA10      = USART1 RX
 * PB0       = WR#
 * PB1       = RD#
 * PB10      = DDIR
 * PB11      = ASEL1
 * PB12      = ASEL0
 * PB13      = ASEN#
 * PB14      = FMOD / P1.7
 * PB15      = P3.6 / FPI ENTER
 * P1.6 / SDA pin 51 MUST REMAIN OPEN.
 */

#include "stm32f1xx.h"
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#ifndef ALLOW_DESTRUCTIVE_FPI
#define ALLOW_DESTRUCTIVE_FPI 0
#endif

#define PROVEN_SST_MFR_ID          0xBFU
#define PROVEN_SST_DEVICE_ID       0xD5U
#define PROVEN_ORIGINAL_CRC32      0xB3680360UL
#define FLASH_ERASED_CRC32         0x154803CCUL  /* CRC32 of 128 KiB of FF */
#define SST_PROGRAM_POLL_LIMIT     500UL
#define SST_ERASE_POLL_LIMIT       10000UL


#define FLASH_MAX_SIZE 0x20000UL

#define PB_WR      0
#define PB_RD      1
#define PB_DDIR   10
#define PB_ASEL1  11
#define PB_ASEL0  12
#define PB_ASEN   13
#define PB_FMOD   14
#define PB_ENTER  15
#define PA_RST     8

static bool fpi_active = false;

/* ---------- basic GPIO ---------- */

static void cfg_pin(GPIO_TypeDef *g, unsigned pin, uint32_t nibble)
{
    volatile uint32_t *cr = (pin < 8) ? &g->CRL : &g->CRH;
    unsigned shift = (pin & 7U) * 4U;
    uint32_t v = *cr;
    v &= ~(0xFUL << shift);
    v |= (nibble & 0xFUL) << shift;
    *cr = v;
}

/* STM32F1 mode nibbles */
#define GPIO_IN_FLOAT   0x4U
#define GPIO_IN_PULL    0x8U
#define GPIO_OUT_PP_10  0x1U
#define GPIO_OUT_OD_10  0x5U
#define GPIO_AF_PP_10   0x9U

static inline void pin_hi(GPIO_TypeDef *g, unsigned pin)
{
    g->BSRR = 1UL << pin;
}

static inline void pin_lo(GPIO_TypeDef *g, unsigned pin)
{
    g->BRR = 1UL << pin;
}

static inline bool pin_is_hi(GPIO_TypeDef *g, unsigned pin)
{
    return (g->IDR & (1UL << pin)) != 0;
}

/* PA0..PA7 only. */
static void bus_input(void)
{
    GPIOA->CRL = 0x44444444UL;
}

static void bus_output(void)
{
    GPIOA->CRL = 0x11111111UL;
}

static void bus_write(uint8_t v)
{
    GPIOA->BSRR = (((uint32_t)(~v) & 0xFFUL) << 16) | (uint32_t)v;
}

static uint8_t bus_read(void)
{
    return (uint8_t)(GPIOA->IDR & 0xFFU);
}

/* Actively drive LOW with open drain. */
static void line_low(GPIO_TypeDef *g, unsigned pin)
{
    pin_lo(g, pin);
    cfg_pin(g, pin, GPIO_OUT_OD_10);
    pin_lo(g, pin);
}

/* Release line. Weak STM32 pull-up prevents a floating local input. */
static void line_release(GPIO_TypeDef *g, unsigned pin)
{
    pin_hi(g, pin);
    cfg_pin(g, pin, GPIO_IN_PULL);
    pin_hi(g, pin);
}

/* ---------- delays: DWT cycle counter ---------- */

static void dwt_init(void)
{
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
}

static void delay_us(uint32_t us)
{
    /* SYSCLK stays at reset-default HSI = 8 MHz. */
    uint32_t start = DWT->CYCCNT;
    uint32_t ticks = us * 8UL;
    while ((uint32_t)(DWT->CYCCNT - start) < ticks) {
        __NOP();
    }
}

/* ---------- USART1 ---------- */

static void uart_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN |
                    RCC_APB2ENR_IOPBEN |
                    RCC_APB2ENR_AFIOEN |
                    RCC_APB2ENR_USART1EN;

    /* PA9 TX AF push-pull 10 MHz; PA10 RX floating input. */
    cfg_pin(GPIOA, 9, GPIO_AF_PP_10);
    cfg_pin(GPIOA,10, GPIO_IN_FLOAT);

    /* APB2 = 8 MHz, 115200 baud => BRR ~= 0x45. */
    USART1->BRR = 0x45;
    USART1->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
}

static void uart_putc(uint8_t c)
{
    while (!(USART1->SR & USART_SR_TXE)) {}
    USART1->DR = c;
}

static void uart_write(const uint8_t *p, uint32_t n)
{
    while (n--) uart_putc(*p++);
    while (!(USART1->SR & USART_SR_TC)) {}
}

static void uart_puts(const char *s)
{
    uart_write((const uint8_t*)s, (uint32_t)strlen(s));
}

static uint8_t uart_getc(void)
{
    while (!(USART1->SR & USART_SR_RXNE)) {}
    return (uint8_t)(USART1->DR & 0xFFU);
}

static int uart_getline(char *buf, int maxlen)
{
    int n = 0;
    for (;;) {
        uint8_t c = uart_getc();
        if (c == '\r') continue;
        if (c == '\n') {
            buf[n] = 0;
            return n;
        }
        if (n < maxlen - 1) {
            buf[n++] = (char)c;
        } else {
            buf[0] = 0;
            return -1;
        }
    }
}

/* ---------- small formatting/parsing ---------- */

static void put_hex_nibble(uint8_t n)
{
    n &= 0x0F;
    uart_putc((uint8_t)(n < 10 ? ('0' + n) : ('A' + n - 10)));
}

static void put_hex8(uint8_t v)
{
    put_hex_nibble(v >> 4);
    put_hex_nibble(v);
}

static void put_hex32(uint32_t v)
{
    for (int s = 28; s >= 0; s -= 4) put_hex_nibble((uint8_t)(v >> s));
}

static bool parse_hex(const char *s, uint32_t *out)
{
    if (!s || !*s || !out) return false;
    if (s[0]=='0' && (s[1]=='x' || s[1]=='X')) s += 2;
    if (!*s) return false;

    uint32_t v = 0;
    while (*s) {
        char c = *s++;
        uint32_t n;
        if (c >= '0' && c <= '9') n = (uint32_t)(c-'0');
        else if (c >= 'a' && c <= 'f') n = (uint32_t)(c-'a'+10);
        else if (c >= 'A' && c <= 'F') n = (uint32_t)(c-'A'+10);
        else return false;
        if (v > 0x0FFFFFFFUL) return false;
        v = (v << 4) | n;
    }
    *out = v;
    return true;
}

static char *next_tok(char **p)
{
    char *s = *p;
    while (*s == ' ' || *s == '\t') s++;
    if (!*s) { *p = s; return 0; }
    char *start = s;
    while (*s && *s != ' ' && *s != '\t') s++;
    if (*s) *s++ = 0;
    *p = s;
    return start;
}

/* ---------- FPI ---------- */

static void fpi_gpio_init(void)
{
    /* Control outputs. */
    cfg_pin(GPIOB, PB_WR,    GPIO_OUT_PP_10);
    cfg_pin(GPIOB, PB_RD,    GPIO_OUT_PP_10);
    cfg_pin(GPIOB, PB_DDIR,  GPIO_OUT_PP_10);
    cfg_pin(GPIOB, PB_ASEL1, GPIO_OUT_PP_10);
    cfg_pin(GPIOB, PB_ASEL0, GPIO_OUT_PP_10);
    cfg_pin(GPIOB, PB_ASEN,  GPIO_OUT_PP_10);

    pin_hi(GPIOB, PB_WR);
    pin_hi(GPIOB, PB_RD);
    pin_hi(GPIOB, PB_DDIR);
    pin_hi(GPIOB, PB_ASEN);
    pin_lo(GPIOB, PB_ASEL1);
    pin_lo(GPIOB, PB_ASEL0);

    bus_input();

    /* FPI mode/reset lines released at power-up. */
    line_release(GPIOA, PA_RST);
    line_release(GPIOB, PB_FMOD);
    line_release(GPIOB, PB_ENTER);
}

static void fpi_enter(void)
{
    pin_hi(GPIOB, PB_WR);
    pin_hi(GPIOB, PB_RD);
    pin_hi(GPIOB, PB_ASEN);
    pin_hi(GPIOB, PB_DDIR);
    pin_lo(GPIOB, PB_ASEL1);
    pin_lo(GPIOB, PB_ASEL0);
    bus_input();

    line_release(GPIOB, PB_FMOD);
    line_release(GPIOB, PB_ENTER);
    line_release(GPIOA, PA_RST);
    delay_us(20);

    line_low(GPIOA, PA_RST);
    delay_us(10);              /* > manual t1 >= 1000 ns */

    line_low(GPIOB, PB_FMOD);  /* P1.7/FMOD low */
    delay_us(10);

    line_low(GPIOB, PB_ENTER); /* P3.6 low */
    delay_us(20);

    fpi_active = true;
}

static void fpi_run(void)
{
    line_low(GPIOA, PA_RST);
    line_release(GPIOB, PB_ENTER);
    line_release(GPIOB, PB_FMOD);

    bus_input();
    pin_hi(GPIOB, PB_WR);
    pin_hi(GPIOB, PB_RD);
    pin_hi(GPIOB, PB_ASEN);
    pin_hi(GPIOB, PB_DDIR);

    delay_us(20);
    line_release(GPIOA, PA_RST);
    fpi_active = false;
}

static void asel(bool a1, bool a0)
{
    if (a1) pin_hi(GPIOB, PB_ASEL1); else pin_lo(GPIOB, PB_ASEL1);
    if (a0) pin_hi(GPIOB, PB_ASEL0); else pin_lo(GPIOB, PB_ASEL0);
    delay_us(2);
}

static void asen_pulse(void)
{
    pin_lo(GPIOB, PB_ASEN);
    delay_us(2);
    pin_hi(GPIOB, PB_ASEN);
    delay_us(2);
}

static void latch_address(uint32_t a)
{
    pin_hi(GPIOB, PB_DDIR);
    bus_output();

    asel(false,false);
    bus_write((uint8_t)a);
    delay_us(2);
    asen_pulse();

    asel(false,true);
    bus_write((uint8_t)(a >> 8));
    delay_us(2);
    asen_pulse();

    asel(true,false);
    bus_write((uint8_t)((a >> 16) & 1U));
    delay_us(2);
    asen_pulse();
}

static uint8_t fpi_read_byte(uint32_t a)
{
    latch_address(a);

    /* Remove STM32 drive before giving bus to Flash. */
    bus_input();
    pin_lo(GPIOB, PB_DDIR);    /* DDIR=0: Flash -> P0 */
    delay_us(2);

    pin_lo(GPIOB, PB_RD);
    delay_us(2);
    uint8_t v = bus_read();
    pin_hi(GPIOB, PB_RD);

    delay_us(2);
    pin_hi(GPIOB, PB_DDIR);
    return v;
}


/*
 * FPI command-register write.
 *
 * IMPORTANT SAFETY DESIGN:
 * This v0.3 firmware does NOT expose a generic host WRITE command.
 * The only call sites below use the JEDEC software-identification bytes:
 *   AA, 55, 90 and F0(reset/read-array).
 * No byte-program (A0) or erase setup/confirm (80/10/30) sequence exists.
 */
static void fpi_command_write(uint32_t a, uint8_t v)
{
    /* ASEN, RD and WR are mutually exclusive according to the Micronas manual. */
    pin_hi(GPIOB, PB_RD);
    pin_hi(GPIOB, PB_WR);
    pin_hi(GPIOB, PB_ASEN);

    latch_address(a);          /* leaves DDIR=1 and PA0..7 as outputs */

    bus_write(v);
    delay_us(2);               /* >> t6 = 90 ns */

    pin_lo(GPIOB, PB_WR);
    delay_us(2);               /* >> t8 = 70 ns */
    pin_hi(GPIOB, PB_WR);

    delay_us(2);               /* >> t7 = 40 ns */
}

/* JEDEC read-array / software-ID exit command. */
static void jedec_reset_read_array(void)
{
    fpi_command_write(0x00000UL, 0xF0U);
    delay_us(20);
}

static void jedec_id_sequence(uint32_t unlock1, uint32_t unlock2)
{
    fpi_command_write(unlock1, 0xAAU);
    fpi_command_write(unlock2, 0x55U);
    fpi_command_write(unlock1, 0x90U);
    delay_us(20);
}

/*
 * Non-destructive probe:
 *   - capture normal bytes 0/1
 *   - force F0/read-array
 *   - issue AA/55/90
 *   - read ID-space bytes 0..3
 *   - exit with F0
 *   - verify normal bytes 0/1 returned
 */
static void cmd_idprobe(uint32_t unlock1, uint32_t unlock2, const char *tag)
{
    if (!fpi_active) fpi_enter();

    uint8_t pre0 = fpi_read_byte(0x00000UL);
    uint8_t pre1 = fpi_read_byte(0x00001UL);

    jedec_reset_read_array();
    jedec_id_sequence(unlock1, unlock2);

    uint8_t id0 = fpi_read_byte(0x00000UL);
    uint8_t id1 = fpi_read_byte(0x00001UL);
    uint8_t id2 = fpi_read_byte(0x00002UL);
    uint8_t id3 = fpi_read_byte(0x00003UL);

    jedec_reset_read_array();

    uint8_t post0 = fpi_read_byte(0x00000UL);
    uint8_t post1 = fpi_read_byte(0x00001UL);

    uart_puts("ID ");
    uart_puts(tag);
    uart_puts(" PRE ");
    put_hex8(pre0); uart_putc(' '); put_hex8(pre1);
    uart_puts(" RAW ");
    put_hex8(id0); uart_putc(' '); put_hex8(id1);
    uart_putc(' '); put_hex8(id2); uart_putc(' '); put_hex8(id3);
    uart_puts(" POST ");
    put_hex8(post0); uart_putc(' '); put_hex8(post1);
    uart_puts("\r\n");

    if (pre0 == post0 && pre1 == post1) uart_puts("IDEXIT OK\r\n");
    else uart_puts("IDEXIT MISMATCH\r\n");
}

/* ---------- CRC32 ---------- */

static uint32_t crc32_byte(uint32_t crc, uint8_t data)
{
    crc ^= data;
    for (unsigned i=0; i<8; ++i)
        crc = (crc >> 1) ^ (0xEDB88320UL & (uint32_t)-(int32_t)(crc & 1U));
    return crc;
}


/* ---------- SST39LF/VF010 programming/recovery engine ---------- */
/*
 * IMPORTANT:
 * The real destructive code is present for review/testing, but the shipped
 * PlatformIO configuration defines ALLOW_DESTRUCTIVE_FPI=0.
 *
 * With ALLOW_DESTRUCTIVE_FPI=0:
 *   - ARM/ERASEGO/PROGRAMIMAGE return ERR COMPILE_LOCK.
 *   - no destructive sequence can be executed from the host.
 *
 * The code below uses only the BF D5 / 5555-2AAA command set proven on the
 * actual SDA555XFL through the non-destructive Software ID probe.
 */

static uint32_t flash_crc32_all(void)
{
    if (!fpi_active) fpi_enter();

    uint32_t crc = 0xFFFFFFFFUL;
    for (uint32_t a = 0; a < FLASH_MAX_SIZE; ++a)
        crc = crc32_byte(crc, fpi_read_byte(a));
    return crc ^ 0xFFFFFFFFUL;
}

static bool flash_all_ff(uint32_t *first_bad_addr, uint8_t *first_bad_value)
{
    if (!fpi_active) fpi_enter();

    for (uint32_t a = 0; a < FLASH_MAX_SIZE; ++a) {
        uint8_t v = fpi_read_byte(a);
        if (v != 0xFFU) {
            if (first_bad_addr) *first_bad_addr = a;
            if (first_bad_value) *first_bad_value = v;
            return false;
        }
    }
    return true;
}

static bool sst_read_proven_id(uint8_t *mfr, uint8_t *dev)
{
    if (!fpi_active) fpi_enter();

    jedec_reset_read_array();
    jedec_id_sequence(0x05555UL, 0x02AAAUL);

    uint8_t a = fpi_read_byte(0x00000UL);
    uint8_t b = fpi_read_byte(0x00001UL);

    jedec_reset_read_array();

    if (mfr) *mfr = a;
    if (dev) *dev = b;
    return a == PROVEN_SST_MFR_ID && b == PROVEN_SST_DEVICE_ID;
}

/*
 * Completion verification:
 * - DQ7 must reach true data (or 1 for erase).
 * - DQ6 must stop toggling.
 * - because write completion is asynchronous, confirm with two more reads.
 * - after Byte Program, require full-byte readback match.
 */
static bool sst_wait_ready(uint32_t addr, uint8_t expected, bool erase,
                           uint32_t poll_limit, uint8_t *last_value)
{
    for (uint32_t i = 0; i < poll_limit; ++i) {
        uint8_t r1 = fpi_read_byte(addr);
        uint8_t r2 = fpi_read_byte(addr);

        bool dq6_stable = ((r1 ^ r2) & 0x40U) == 0;
        bool dq7_true = erase
            ? ((r2 & 0x80U) != 0)
            : ((r2 & 0x80U) == (expected & 0x80U));

        if (dq6_stable && dq7_true) {
            /* Datasheet warns of the asynchronous completion boundary. */
            delay_us(2);
            uint8_t r3 = fpi_read_byte(addr);
            uint8_t r4 = fpi_read_byte(addr);

            bool dq6_stable2 = ((r3 ^ r4) & 0x40U) == 0;
            bool dq7_true2 = erase
                ? ((r4 & 0x80U) != 0)
                : ((r4 & 0x80U) == (expected & 0x80U));

            if (dq6_stable2 && dq7_true2) {
                if (last_value) *last_value = r4;
                if (erase) return true;

                /* All bits may trail DQ7 by up to about 1 us. */
                delay_us(2);
                uint8_t rb = fpi_read_byte(addr);
                if (last_value) *last_value = rb;
                return rb == expected;
            }
        }
    }

    if (last_value) *last_value = fpi_read_byte(addr);
    return false;
}

#if ALLOW_DESTRUCTIVE_FPI

static bool sst_byte_program(uint32_t addr, uint8_t data, uint8_t *readback)
{
    if (addr >= FLASH_MAX_SIZE) return false;

    /* Never try to program FF; it is already the erased state. */
    if (data == 0xFFU) {
        uint8_t rb = fpi_read_byte(addr);
        if (readback) *readback = rb;
        return rb == 0xFFU;
    }

    /* Enforce Flash physics before issuing any command. */
    uint8_t before = fpi_read_byte(addr);
    if ((before & data) != data) {
        if (readback) *readback = before;
        return false; /* would require 0 -> 1 */
    }

    fpi_command_write(0x05555UL, 0xAAU);
    fpi_command_write(0x02AAAUL, 0x55U);
    fpi_command_write(0x05555UL, 0xA0U);
    fpi_command_write(addr, data);

    uint8_t last = 0;
    bool ok = sst_wait_ready(addr, data, false, SST_PROGRAM_POLL_LIMIT, &last);
    if (readback) *readback = last;
    return ok;
}

static bool sst_chip_erase(uint32_t *first_bad_addr, uint8_t *first_bad_value)
{
    /* SST requires at least 100 us after power-up before Program/Erase. */
    delay_us(200);

    fpi_command_write(0x05555UL, 0xAAU);
    fpi_command_write(0x02AAAUL, 0x55U);
    fpi_command_write(0x05555UL, 0x80U);
    fpi_command_write(0x05555UL, 0xAAU);
    fpi_command_write(0x02AAAUL, 0x55U);
    fpi_command_write(0x05555UL, 0x10U);

    uint8_t last = 0;
    if (!sst_wait_ready(0x00000UL, 0xFFU, true,
                        SST_ERASE_POLL_LIMIT, &last))
        return false;

    /* Strong postcondition: verify every byte is FF. */
    return flash_all_ff(first_bad_addr, first_bad_value);
}

static bool destructive_session_armed = false;
static bool destructive_session_erased = false;
static uint32_t destructive_expected_current_crc = 0;
static uint32_t destructive_expected_target_crc = 0;

static void destructive_disarm(void)
{
    destructive_session_armed = false;
    destructive_session_erased = false;
    destructive_expected_current_crc = 0;
    destructive_expected_target_crc = 0;
}

static void cmd_arm(uint32_t expected_current_crc, uint32_t expected_target_crc)
{
    destructive_disarm();

    uint8_t mfr = 0, dev = 0;
    if (!sst_read_proven_id(&mfr, &dev)) {
        uart_puts("ERR ID ");
        put_hex8(mfr); uart_putc(' '); put_hex8(dev);
        uart_puts("\r\n");
        return;
    }

    uint32_t live_crc = flash_crc32_all();
    if (live_crc != expected_current_crc) {
        uart_puts("ERR CURRENT_CRC ");
        put_hex32(live_crc);
        uart_puts("\r\n");
        return;
    }

    destructive_expected_current_crc = expected_current_crc;
    destructive_expected_target_crc = expected_target_crc;
    destructive_session_armed = true;

    uart_puts("ARMED BF D5 CURRENT ");
    put_hex32(live_crc);
    uart_puts(" TARGET ");
    put_hex32(expected_target_crc);
    uart_puts("\r\n");
}

static void cmd_erasego(uint32_t current_crc, uint32_t target_crc, const char *magic)
{
    if (!destructive_session_armed ||
        current_crc != destructive_expected_current_crc ||
        target_crc != destructive_expected_target_crc) {
        uart_puts("ERR NOT_ARMED\r\n");
        return;
    }

    if (!magic || strcmp(magic, "SST39_BFD5_ERASE") != 0) {
        uart_puts("ERR MAGIC\r\n");
        return;
    }

    /* Re-check the live array immediately before destructive operation. */
    uint32_t live_crc = flash_crc32_all();
    if (live_crc != current_crc) {
        destructive_disarm();
        uart_puts("ERR LIVE_CHANGED ");
        put_hex32(live_crc);
        uart_puts("\r\n");
        return;
    }

    uint8_t mfr = 0, dev = 0;
    if (!sst_read_proven_id(&mfr, &dev)) {
        destructive_disarm();
        uart_puts("ERR ID\r\n");
        return;
    }

    uint32_t bad_addr = 0;
    uint8_t bad_val = 0;
    if (!sst_chip_erase(&bad_addr, &bad_val)) {
        destructive_disarm();
        uart_puts("ERR ERASE_VERIFY ");
        put_hex32(bad_addr); uart_putc(' '); put_hex8(bad_val);
        uart_puts("\r\n");
        return;
    }

    uint32_t erased_crc = flash_crc32_all();
    if (erased_crc != FLASH_ERASED_CRC32) {
        destructive_disarm();
        uart_puts("ERR ERASED_CRC ");
        put_hex32(erased_crc);
        uart_puts("\r\n");
        return;
    }

    destructive_session_erased = true;
    uart_puts("ERASED FF CRC ");
    put_hex32(erased_crc);
    uart_puts("\r\nOK\r\n");
}

static void cmd_programimage(uint32_t size, uint32_t target_crc, const char *magic)
{
    if (!destructive_session_armed || !destructive_session_erased) {
        uart_puts("ERR NOT_ERASED\r\n");
        return;
    }

    if (size != FLASH_MAX_SIZE || target_crc != destructive_expected_target_crc) {
        uart_puts("ERR TARGET\r\n");
        return;
    }

    if (!magic || strcmp(magic, "SST39_BFD5_PROGRAM") != 0) {
        uart_puts("ERR MAGIC\r\n");
        return;
    }

    uart_puts("READY BINARY 00020000\r\n");

    uint32_t incoming_crc = 0xFFFFFFFFUL;
    uint32_t programmed = 0;
    bool failed = false;
    uint32_t fail_addr = 0;
    uint8_t fail_wanted = 0;
    uint8_t fail_got = 0;

    /*
     * Always drain the full image even if one byte fails, so UART framing
     * remains synchronized and the host can receive a deterministic result.
     */
    for (uint32_t a = 0; a < FLASH_MAX_SIZE; ++a) {
        uint8_t d = uart_getc();
        incoming_crc = crc32_byte(incoming_crc, d);

        if (!failed && d != 0xFFU) {
            uint8_t rb = 0;
            if (!sst_byte_program(a, d, &rb)) {
                failed = true;
                fail_addr = a;
                fail_wanted = d;
                fail_got = rb;
            } else {
                ++programmed;
            }
        }
    }
    incoming_crc ^= 0xFFFFFFFFUL;

    if (incoming_crc != target_crc) {
        destructive_disarm();
        uart_puts("ERR STREAM_CRC ");
        put_hex32(incoming_crc);
        uart_puts("\r\n");
        return;
    }

    if (failed) {
        destructive_disarm();
        uart_puts("ERR PROGRAM ");
        put_hex32(fail_addr); uart_putc(' ');
        put_hex8(fail_wanted); uart_putc(' '); put_hex8(fail_got);
        uart_puts("\r\n");
        return;
    }

    uint32_t flash_crc = flash_crc32_all();
    if (flash_crc != target_crc) {
        destructive_disarm();
        uart_puts("ERR FLASH_CRC ");
        put_hex32(flash_crc);
        uart_puts("\r\n");
        return;
    }

    uart_puts("PROGRAMMED ");
    put_hex32(programmed);
    uart_puts(" FLASHCRC ");
    put_hex32(flash_crc);
    uart_puts("\r\nOK\r\n");

    destructive_disarm();
}

#endif /* ALLOW_DESTRUCTIVE_FPI */

/* ---------- destructive-command DRY-RUN planner ---------- */
/*
 * These routines PRINT the exact SST39LF/VF010 command sequence proven
 * by Software ID BF D5. They DO NOT call fpi_command_write().
 */
static void plan_step(uint32_t a, uint8_t d)
{
    uart_puts("STEP ");
    put_hex32(a);
    uart_putc(' ');
    put_hex8(d);
    uart_puts("\r\n");
}

static void cmd_planbyte(uint32_t a, uint8_t d)
{
    if (a >= FLASH_MAX_SIZE) { uart_puts("ERR RANGE\r\n"); return; }
    uart_puts("PLAN BYTEPROGRAM SST39LF/VF010\r\n");
    plan_step(0x05555UL, 0xAAU);
    plan_step(0x02AAAUL, 0x55U);
    plan_step(0x05555UL, 0xA0U);
    plan_step(a, d);
    uart_puts("POLL DQ7/DQ6 THEN READBACK VERIFY\r\n");
    uart_puts("DRYRUN ONLY - NO WR PULSE\r\nOK\r\n");
}

static void cmd_planerase(void)
{
    uart_puts("PLAN CHIPERASE SST39LF/VF010\r\n");
    plan_step(0x05555UL, 0xAAU);
    plan_step(0x02AAAUL, 0x55U);
    plan_step(0x05555UL, 0x80U);
    plan_step(0x05555UL, 0xAAU);
    plan_step(0x02AAAUL, 0x55U);
    plan_step(0x05555UL, 0x10U);
    uart_puts("POLL DQ7/DQ6 THEN FULL-ARRAY FF VERIFY\r\n");
    uart_puts("DRYRUN ONLY - NO WR PULSE\r\nOK\r\n");
}

/* ---------- protocol ---------- */

static void cmd_info(void)
{
    uart_puts(
        "S55FPI STM32F103 ENGINE 0.5\r\n"
        "TARGET SDA555xFL\r\n"
        "MAX_FLASH 00020000\r\n"
        "UART 115200 8N1\r\n"
        "BUS PA0..PA7\r\n"
        "P1.6 MUST REMAIN OPEN\r\n"
        "RUNTIME REGISTER_LEVEL\r\n"
        "ID PROBE WRITES ONLY: AA 55 90 F0\r\n"
        "REAL SST ENGINE SOURCE: PRESENT\r\n"
#if ALLOW_DESTRUCTIVE_FPI
        "DESTRUCTIVE ENGINE: ENABLED\r\n"
#else
        "DESTRUCTIVE ENGINE: COMPILE-LOCKED\r\n"
#endif
        "PLANBYTE/PLANERASE ALWAYS AVAILABLE\r\n"
        "OK\r\n"
    );
}

static void cmd_peek(uint32_t a)
{
    if (a >= FLASH_MAX_SIZE) { uart_puts("ERR RANGE\r\n"); return; }
    if (!fpi_active) fpi_enter();

    uint8_t v = fpi_read_byte(a);
    uart_puts("BYTE ");
    put_hex32(a);
    uart_putc(' ');
    put_hex8(v);
    uart_puts("\r\n");
}

static void cmd_read(uint32_t a, uint32_t n)
{
    if (!n || a >= FLASH_MAX_SIZE || n > FLASH_MAX_SIZE || a+n > FLASH_MAX_SIZE) {
        uart_puts("ERR RANGE\r\n");
        return;
    }

    if (!fpi_active) fpi_enter();

    uart_puts("DATA ");
    put_hex32(a);
    uart_putc(' ');
    put_hex32(n);
    uart_puts("\r\n");

    uint32_t crc = 0xFFFFFFFFUL;
    for (uint32_t i=0; i<n; ++i) {
        uint8_t v = fpi_read_byte(a+i);
        crc = crc32_byte(crc, v);
        uart_putc(v);
    }
    while (!(USART1->SR & USART_SR_TC)) {}

    crc ^= 0xFFFFFFFFUL;
    uart_puts("\r\nCRC32 ");
    put_hex32(crc);
    uart_puts("\r\n");
}

static void process_line(char *line)
{
    char *p=line;
    char *cmd=next_tok(&p);
    if (!cmd) return;

    if (!strcmp(cmd,"INFO")) { cmd_info(); return; }

    if (!strcmp(cmd,"ENTER")) {
        fpi_enter();
        uart_puts("OK FPI\r\n");
        return;
    }

    if (!strcmp(cmd,"RUN")) {
        fpi_run();
        uart_puts("OK RUN\r\n");
        return;
    }

    if (!strcmp(cmd,"PEEK")) {
        char *sa=next_tok(&p);
        uint32_t a;
        if (!parse_hex(sa,&a)) { uart_puts("ERR ARG\r\n"); return; }
        cmd_peek(a);
        return;
    }

    if (!strcmp(cmd,"READ")) {
        char *sa=next_tok(&p), *sn=next_tok(&p);
        uint32_t a,n;
        if (!parse_hex(sa,&a) || !parse_hex(sn,&n)) {
            uart_puts("ERR ARG\r\n"); return;
        }
        cmd_read(a,n);
        return;
    }

    /*
     * Two historical JEDEC unlock-address conventions found in 1-Mbit x8
     * 3-V Flash families. Both probes use only AA/55/90/F0.
     *
     * ID5555: SST/Atmel-style 5555h / 2AAAh
     * ID0555: AMD/ST-style   0555h / 02AAh
     */
    if (!strcmp(cmd,"ID5555")) {
        cmd_idprobe(0x05555UL, 0x02AAAUL, "5555");
        return;
    }

    if (!strcmp(cmd,"ID0555")) {
        cmd_idprobe(0x00555UL, 0x002AAUL, "0555");
        return;
    }

    if (!strcmp(cmd,"PLANBYTE")) {
        char *sa=next_tok(&p), *sd=next_tok(&p);
        uint32_t a,d;
        if (!parse_hex(sa,&a) || !parse_hex(sd,&d) || d > 0xFFU) {
            uart_puts("ERR ARG\r\n"); return;
        }
        cmd_planbyte(a,(uint8_t)d);
        return;
    }
    if (!strcmp(cmd,"PLANERASE")) {
        cmd_planerase();
        return;
    }
    if (!strcmp(cmd,"ENGINESTATUS")) {
#if ALLOW_DESTRUCTIVE_FPI
        uart_puts("ENGINE ENABLED\r\n");
#else
        uart_puts("ENGINE COMPILE_LOCKED\r\n");
#endif
        uart_puts("ID BF D5; UNLOCK 5555/2AAA\r\n");
        uart_puts("PROGRAM AA 55 A0; ERASE AA 55 80 AA 55 10\r\n");
        uart_puts("OK\r\n");
        return;
    }

    if (!strcmp(cmd,"ARM")) {
        char *sc=next_tok(&p), *st=next_tok(&p);
        uint32_t current_crc,target_crc;
        if (!parse_hex(sc,&current_crc) || !parse_hex(st,&target_crc)) {
            uart_puts("ERR ARG\r\n");
            return;
        }
#if ALLOW_DESTRUCTIVE_FPI
        cmd_arm(current_crc,target_crc);
#else
        uart_puts("ERR COMPILE_LOCK\r\n");
#endif
        return;
    }

    if (!strcmp(cmd,"ERASEGO")) {
        char *sc=next_tok(&p), *st=next_tok(&p), *magic=next_tok(&p);
        uint32_t current_crc,target_crc;
        if (!parse_hex(sc,&current_crc) || !parse_hex(st,&target_crc) || !magic) {
            uart_puts("ERR ARG\r\n");
            return;
        }
#if ALLOW_DESTRUCTIVE_FPI
        cmd_erasego(current_crc,target_crc,magic);
#else
        uart_puts("ERR COMPILE_LOCK\r\n");
#endif
        return;
    }

    if (!strcmp(cmd,"PROGRAMIMAGE")) {
        char *ss=next_tok(&p), *st=next_tok(&p), *magic=next_tok(&p);
        uint32_t size,target_crc;
        if (!parse_hex(ss,&size) || !parse_hex(st,&target_crc) || !magic) {
            uart_puts("ERR ARG\r\n");
            return;
        }
#if ALLOW_DESTRUCTIVE_FPI
        cmd_programimage(size,target_crc,magic);
#else
        uart_puts("ERR COMPILE_LOCK\r\n");
#endif
        return;
    }

    if (!strcmp(cmd,"ERASE") || !strcmp(cmd,"PROGRAM") || !strcmp(cmd,"WRITE")) {
        uart_puts("ERR USE_GATED_ENGINE\r\n");
        return;
    }

    uart_puts("ERR CMD\r\n");
}

int main(void)
{
    /*
     * STM32F103 starts from internal HSI 8 MHz after reset.
     * Do not enable PLL or SysTick.
     */
    uart_init();
    dwt_init();
    fpi_gpio_init();

    uart_puts("S55FPI STM32F103 ENGINE 0.5 READY\r\n");

    char line[96];
    for (;;) {
        int n = uart_getline(line, sizeof(line));
        if (n >= 0) process_line(line);
        else uart_puts("ERR LINE\r\n");
    }
}
