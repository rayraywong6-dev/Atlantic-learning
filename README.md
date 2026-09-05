# Atlantic Learning

一个自动更新的《大西洋月刊》（The Atlantic）英文学习资料库。

## 收集范围

本项目读取 The Atlantic 的公开 RSS，只保存公开提供的：

- 文章标题
- 作者与发布日期
- 栏目
- RSS 摘要
- 原文链接

它不会绕过登录、订阅或付费墙，也不会复制未公开授权的完整文章。

## 自动更新

GitHub Actions 每天北京时间 08:15 左右运行，也可在 Actions 页面手动运行 `Update Atlantic learning library`。

抓取结果保存在：

- `docs/data/articles.json`
- `docs/index.html`（可搜索、筛选的学习页面）

## 本地运行

需要 Python 3.10 或更高版本，无第三方依赖：

```bash
python fetch_atlantic.py
```

## 数据源

- All Articles
- Best of The Atlantic
- Business
- Technology
- Education
- Global

所有文章版权归 The Atlantic 及原作者所有。请通过页面中的原文链接阅读正文。
