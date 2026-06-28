import urllib.request
import socket
import sys

def get_public_ip():
    """Определяет публичный IP через внешние сервисы с резервным каналом."""
    services = [
        'https://api.ipify.org',
        'https://ifconfig.me/ip',
        'https://ident.me',
        'https://icanhazip.com'
    ]
    
    for service in services:
        try:
            with urllib.request.urlopen(service, timeout=5) as response:
                ip = response.read().decode('utf-8').strip()
                if ip: return ip
        except Exception:
            continue
    return None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "не определен"

if __name__ == "__main__":
    public_ip = get_public_ip()
    local_ip = get_local_ip()
    
    print("\n" + "="*60)
    print(" КРИТИЧЕСКАЯ ИНФОРМАЦИЯ ДЛЯ БОТА")
    print("="*60)
    
    if public_ip:
        print(f" ВАШ ПУБЛИЧНЫЙ IP (для биржи):  {public_ip}")
        print("-" * 60)
        print(" СОВЕТ: Вставьте этот IP в White List (белый список) в настройках")
        print(" API-ключа на бирже. Это обезопасит ваши средства.")
    else:
        print(" ОШИБКА: Не удалось определить публичный IP!")
        print(" Проверьте доступ сервера к интернету.")
        
    print(f"\n Внутренний IP сервера: {local_ip} (для биржи НЕ НУЖЕН)")
    print("="*60 + "\n")


# # chmod 600 ssh_key.txt
# # eval "$(ssh-agent -s)" 
# # ssh-add ssh_key.txt
# # git remote set-url origin git@github.com:hotelUpz/uranus_bot.git
# # source .ssh-autostart.sh
# # git push --set-upstream origin master
# # git config --global push.autoSetupRemote true
# # ssh -T git@github.com 
# # git log -1

# # git add .
# # git commit -m "plh37"
# # git push

# # pip install anthropic
# # npm install -g @anthropic-ai/claude-code

# # export ANTHROPIC_API_KEY=...
# taskkill /F /IM python.exe

# # claude