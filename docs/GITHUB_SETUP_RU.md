# Создание удалённого GitHub-репозитория

Рекомендуемое имя: `irman100/SDA555XFL-OSD-Lab`; видимость: **Private**.

## 1. Создать пустой репозиторий

Открой https://github.com/new, выбери владельца `irman100`, имя `SDA555XFL-OSD-Lab`, включи `Private`. Не добавляй README, `.gitignore` или лицензию — они уже находятся в этом наборе.

## 2. Отправить проект с Windows

Распакуй ZIP так, чтобы папка проекта была `D:\SDA555XFL-OSD-Lab`. Открой PowerShell и выполни блок целиком:

```powershell
Set-Location 'D:\SDA555XFL-OSD-Lab'
git init -b main
git add .
git commit -m 'Initial import: SDA555XFL OSD Lab'
git remote add origin 'https://github.com/irman100/SDA555XFL-OSD-Lab.git'
git push -u origin main
```

Если `git commit` сообщит, что не задано имя/почта, используй уже настроенные Git identity локально; не записывай токены или пароли в файлы проекта. Если GitHub запросит вход, пройди стандартную авторизацию через браузер/Git Credential Manager.

## 3. Проверка

После успешного `git push` открой `https://github.com/irman100/SDA555XFL-OSD-Lab`. Убедись, что репозиторий помечен как `Private`, а в корне есть `README.md`.

**Безопасность содержимого:** оригинальный дамп ROM, сервисный PDF телевизора и локальные резервные копии намеренно не включены. Не добавляй заводской дамп в публичный репозиторий.
