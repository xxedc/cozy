# 🚀 VPN Shop Bot 完整恢复指南

## 📋 恢复前准备

### 新服务器要求
- 系统：Ubuntu 22.04 LTS
- 内存：1GB 以上
- 硬盘：20GB 以上
- 开放端口：80、443、8443

### 需要准备
- 新服务器 IP
- 新域名（或沿用旧域名）
- GitHub Token（用于克隆私有仓库）

---

## 🔄 一键恢复步骤

**第1步：连接新服务器**

    ssh root@新服务器IP

**第2步：克隆仓库**

    git clone https://xxedc:你的TOKEN@github.com/xxedc/cozy.git /opt/telegram-vpn-shop
    cd /opt/telegram-vpn-shop

**第3步：运行恢复脚本**

    bash RESTORE_FULL.sh

**第4步：修改域名配置**

    nano /opt/telegram-vpn-shop/.env
    # 修改 MARZBAN_HOST=https://你的新域名

    nano /opt/marzban/.env
    # 修改域名相关配置

**第5步：配置域名DNS**

将域名A记录解析到新服务器IP，等待5-10分钟生效

**第6步：申请SSL证书**

    certbot certonly --standalone -d 你的域名
    cp /etc/letsencrypt/live/你的域名/fullchain.pem /var/lib/marzban/certs/
    cp /etc/letsencrypt/live/你的域名/privkey.pem /var/lib/marzban/certs/

**第7步：重启所有服务**

    systemctl restart vpnshop
    cd /opt/marzban && docker-compose restart

**第8步：验证恢复**

    systemctl status vpnshop
    docker ps | grep marzban

---

## 📁 备份文件说明

| 文件/目录 | 说明 |
|-----------|------|
| src/ | 机器人核心代码 |
| .env.backup | 机器人环境配置（含Bot Token） |
| backup_data.json | 机器人数据库JSON导出 |
| shop.db | 机器人SQLite数据库 |
| restore.py | 数据库恢复脚本 |
| vpnshop.service | systemd服务配置 |
| marzban-config/ | Marzban面板所有配置文件 |
| marzban-config/.env.marzban | Marzban环境配置（含管理员密码） |
| marzban-config/docker-compose.yml | Docker启动配置 |
| marzban-config/admin.py | 修改过的管理面板（中文化） |
| marzban-config/keyboard.py | 面板键盘配置 |
| marzban-data/db.sqlite3 | Marzban数据库（含所有节点用户） |
| marzban-data/xray_config.json | Xray节点协议配置 |
| marzban-data/certs/ | SSL证书文件 |
| RESTORE_FULL.sh | 一键恢复脚本 |
| auto-backup.sh | 每日自动备份脚本 |

---

## 🆘 常见问题处理

**机器人没有响应**

    journalctl -u vpnshop -n 50 --no-pager
    systemctl restart vpnshop

**Marzban面板无法访问**

    docker logs marzban-marzban-1
    cd /opt/marzban && docker-compose down && docker-compose up -d

**订阅链接无效**

    cd /opt/telegram-vpn-shop
    python3 -c "
    import asyncio
    async def sync():
        from src.database.core import init_db
        await init_db()
        from src.scheduler import sync_subscription_urls
        await sync_subscription_urls()
        print('同步完成')
    asyncio.run(sync())
    "

**SSL证书过期**

    certbot renew
    cp /etc/letsencrypt/live/你的域名/fullchain.pem /var/lib/marzban/certs/
    cp /etc/letsencrypt/live/你的域名/privkey.pem /var/lib/marzban/certs/
    cd /opt/marzban && docker-compose restart

---

## ⚠️ 重要注意事项

1. 恢复后必须修改域名，否则节点无法连接
2. SSL证书与域名绑定，新服务器必须重新申请
3. Bot Token无需修改，与服务器IP无关
4. Marzban管理员账号密码在 marzban-config/.env.marzban 中查看
5. 每天凌晨3点自动备份推送到GitHub

---

## 📞 技术支持

如有问题请联系管理员 @xxedce
