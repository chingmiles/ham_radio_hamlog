# HamLog Prototype v2.5

本版本重点：

- 全站移动端适配，桌面端布局尽量保持原样
- 顶部导航支持手机折叠菜单
- QSO 列表 / 访客页 / 控制台最近通联支持移动端卡片视图
- 详情页附件区支持移动端卡片视图
- 新增 / 编辑 QSO 表单在手机端自动单列展示
- 修复 qso_form.html 标题块异常混入脚本的问题

## 启动

```bash
docker compose up -d --build
```

默认访问：

- 管理后台：`http://你的IP:5050/login`
- 访客页：`http://你的IP:5050/public`

## 升级建议

升级前先备份：

```bash
cp -r app/data app/data.bak
cp -r app/uploads app/uploads.bak
```

再覆盖新版文件并执行：

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```


## v2.6
- 移动端 UTC 自动填充改为纯 UTC 文本逻辑，避免原生时间控件受本地时区影响。
- QSO 编辑页按更标准的日志顺序重排，接近常见在线日志编辑逻辑。
- UTC 时间支持 HH:MM:SS，并兼容 0333 / 03:33 / 03:33:25 自动规范化。
