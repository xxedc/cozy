#!/bin/bash
set -e

echo "========================================"
echo "   VPN Shop Bot 完整恢复脚本 v1.0"
echo "========================================"
echo ""

echo "[1/8] 更新系统并安装依赖..."
apt update -y
apt install -y python3 python3-pip git curl wget nginx certbot docker.io docker-compose ufw
echo "✅ 依赖安装完成"

echo "[2/8] 配置防火墙..."
ufw allow 22
ufw allow 80
ufw allow 443
ufw allow 8443
ufw --force enable
echo "✅ 防火墙配置完成"

echo "[3/8] 安装 Python 依赖..."
cd /opt/telegram-vpn-shop
pip3 install -r requirements.txt --break-system-packages
pip3 install aiosqlite qrcode[pil] --break-system-packages
echo "✅ Python 依赖安装完成"

echo "[4/8] 恢复机器人配置..."
if [ -f ".env.backup" ]; then
    cp .env.backup .env
    echo "✅ .env 配置已恢复"
else
    echo "❌ 未找到 .env.backup，请手动创建 .env"
    exit 1
fi

echo "[5/8] 恢复机器人数据库..."
python3 restore.py
echo "✅ 数据库恢复完成"

echo "[6/8] 恢复 Marzban 面板..."
mkdir -p /opt/marzban
mkdir -p /var/lib/marzban/certs
cp marzban-config/.env.marzban /opt/marzban/.env
cp marzban-config/docker-compose.yml /opt/marzban/
cp marzban-config/admin.py /opt/marzban/
cp marzban-config/keyboard.py /opt/marzban/
cp marzban-config/shared.py /opt/marzban/
cp marzban-config/patch_admin.py /opt/marzban/
cp marzban-config/report.py /opt/marzban/
cp marzban-data/db.sqlite3 /var/lib/marzban/
cp marzban-data/xray_config.json /var/lib/marzban/
if [ "$(ls -A marzban-data/certs/ 2>/dev/null)" ]; then
    cp -r marzban-data/certs/* /var/lib/marzban/certs/
fi
echo "✅ Marzban 配置恢复完成"

echo "[7/8] 启动 Marzban..."
cd /opt/marzban
docker-compose up -d
sleep 10
if docker ps | grep -q marzban; then
    echo "✅ Marzban 启动成功"
else
    echo "❌ Marzban 启动失败，请检查: docker logs marzban-marzban-1"
fi
cd /opt/telegram-vpn-shop

echo "[8/8] 启动机器人服务..."
cp vpnshop.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable vpnshop
systemctl start vpnshop
sleep 3
if systemctl is-active --quiet vpnshop; then
    echo "✅ 机器人启动成功"
else
    echo "❌ 机器人启动失败，请检查: journalctl -u vpnshop -n 20"
fi

chmod +x auto-backup.sh
cp auto-backup.sh /opt/auto-backup.sh
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/auto-backup.sh") | crontab -
echo "✅ 自动备份已设置（每天03:00）"

echo ""
echo "========================================"
echo "✅ 基础恢复完成！"
echo "========================================"
echo ""
echo "还需要手动完成以下步骤："
echo ""
echo "1. 修改机器人域名："
echo "   nano /opt/telegram-vpn-shop/.env"
echo "   MARZBAN_HOST=https://你的新域名"
echo ""
echo "2. 修改 Marzban 域名："
echo "   nano /opt/marzban/.env"
echo ""
echo "3. DNS 解析到新服务器 IP"
echo ""
echo "4. 申请 SSL 证书："
echo "   certbot certonly --standalone -d 你的域名"
echo "   cp /etc/letsencrypt/live/域名/fullchain.pem /var/lib/marzban/certs/"
echo "   cp /etc/letsencrypt/live/域名/privkey.pem /var/lib/marzban/certs/"
echo ""
echo "5. 重启服务："
echo "   systemctl restart vpnshop"
echo "   cd /opt/marzban && docker-compose restart"
echo ""
echo "详细说明请查看 RESTORE.md"
