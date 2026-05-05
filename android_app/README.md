# 论文降重助手 - Android APP

**作者: onegod**

基于 KivyMD 构建的 Android 论文降重工具，支持全文改写、选中改写和查重报告降重。

---

## 📥 获取APK的两种方式

### 方式一：GitHub Actions 自动构建（推荐）

1. **创建 GitHub 仓库**
   ```
   https://github.com/你的用户名/paper-rewriter
   ```

2. **推送代码**
   ```bash
   cd C:\Users\Administrator\paper-rewriter
   git init
   git add .
   git commit -m "初始提交"
   git remote add origin https://github.com/你的用户名/paper-rewriter.git
   git push -u origin main
   ```

3. **触发构建**
   - 打开 GitHub 仓库页面
   - 点击 **Actions** 标签
   - 左侧选择 **构建 Android APK**
   - 点击 **Run workflow** → **Run workflow**
   - 等待约 20-30 分钟构建完成
   - 构建完成后，在 Actions 页面点击运行记录
   - 在 **Artifacts** 部分下载 `论文降重助手-APK.zip`

4. **安装到手机**
   - 解压 ZIP 文件
   - 将 `.apk` 文件传到手机
   - 在文件管理器中点击安装

### 方式二：自行使用 Buildozer 构建

如果你有 Linux 环境（或 WSL），可以直接构建：

```bash
# 安装依赖
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
pip install buildozer cython virtualenv

# 构建APK
cd android_app
buildozer android debug

# APK 生成在 bin/ 目录
ls bin/*.apk
```

---

## 📱 功能说明

| 功能 | 说明 |
|------|------|
| **📄 全文降重** | 在输入框中粘贴全文，点击按钮一键改写 |
| **✂️ 选中降重** | 用手指选中文字，只改写选中的部分 |
| **📋 查重降重** | 粘贴查重报告的重复句子，自动匹配并改写 |
| **本地引擎** | 内置同义词库，无需网络，完全免费 |
| **AI增强** | 可配置 OpenAI/Claude/DeepSeek API，效果更好 |
| **AI率评估** | 改写前后AI疑似率对比显示 |

---

## 🔧 技术栈

- **前端**: KivyMD (Material Design)
- **核心引擎**: Python (同义词替换 + 句式变换)
- **构建工具**: Buildozer + python-for-android
- **最低兼容**: Android 6.0 (API 21)
- **目标架构**: arm64-v8a
