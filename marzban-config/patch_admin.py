
import re

fname = '/code/app/telegram/handlers/admin.py'
with open(fname, encoding='utf-8') as f:
    c = f.read()

replacements = [
    ('Bot reload detected. Please start over.', '检测到 Bot 重启，请重新操作。'),
    ('No inbounds selected.', '未选择任何入站。'),
    ('User not found!', '用户不存在！'),
    ('User updated successfully.', '用户更新成功。'),
    ('Username already exists.', '用户名已存在。'),
    ('Subscription Successfully Revoked!', '订阅链接已重置！'),
    ('Users Deleted', '个用户已删除'),
    ('Users Successfully', '个用户操作成功'),
    ('Unsuccessful:', '失败数：'),
    ('In Progress...', '处理中...'),
    ('You must pass some usernames', '请提供用户名'),
    ('User «', '用户 «'),
    ('» not found.', '» 不存在。'),
    ('Last status', '修改前'),
    ('New status', '修改后'),
    ('Traffic Limit :', '流量限额：'),
    ('Expire Date :', '到期日期：'),
    ('"Unlimited"', '"无限制"'),
    ('"Never"', '"永不"'),
    ('"Active"', '"活跃"'),
    ('On Hold', '暂停中'),
    ('Username :', '用户名：'),
    ('Status :', '状态：'),
    ('Traffic Limit:', '流量限额：'),
    ('On Hold Expire Duration :', '暂停时长：'),
    ('On Hold Timeout :', '自动启用时间：'),
    ('Expire Date:', '到期日期：'),
    ('Proxies :', '协议：'),
    ('By :', '操作人：'),
    ('Protocol ', '协议 '),
    (' is disabled on your server', ' 在服务器上未启用'),
    ('Last Traffic Limit :', '修改前流量：'),
    ('New Traffic Limit :', '修改后流量：'),
    ('Last Expire Date :', '修改前到期：'),
    ('New Expire Date :', '修改后到期：'),
    ('Last Proxies :', '修改前协议：'),
    ('New Proxies :', '修改后协议：'),
    ('Count:', '数量：'),
    ('According to:', '变更幅度：'),
    ('Days', '天'),
    ('days', '天'),
    ('Inbound:', '入站：'),
]

for old, new in replacements:
    c = c.replace(old, new)

with open(fname, 'w', encoding='utf-8') as f:
    f.write(c)

print('admin.py patched')
