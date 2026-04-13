# HamLog

- 全站移动端适配，桌面端布局尽量保持原样
- 顶部导航支持手机折叠菜单
- QSO 列表 / 访客页 / 控制台最近通联支持移动端卡片视图
- 详情页附件区支持移动端卡片视图
- 新增 / 编辑 QSO 表单在手机端自动单列展示
- 修复 qso_form.html 标题块异常混入脚本的问题

## 部署
```bash
git clone https://github.com/chingmiles/ham_radio_hamlog.git
cd ham_radio_hamlog
docker compose up -d --build
```

默认访问：

- 管理后台：`http://你的IP:5050/login`
- 访客页：`http://你的IP:5050/public`
