"""
论文降重助手 - Android APP
作者: onegod
基于 KivyMD 构建
"""

import sys
import os
import re
import json
import threading

# 添加父目录到路径，复用核心引擎
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kivy.config import Config
Config.set('kivy', 'window_icon', '')
Config.set('kivy', 'exit_on_escape', True)

from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton, MDFloatingActionButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.tabs import MDTabs, MDTabsBase
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.card import MDCard
from kivymd.uix.segmentedcontrol import MDSegmentedControl, MDSegmentedControlItem
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.list import OneLineListItem
from kivymd import themes

# 导入核心引擎
from rewriter_local import LocalRewriter
from rewriter_api import ApiRewriter
from utils import estimate_ai_probability


# ==================== 主屏幕 ====================

class MainScreen(MDScreen):
    """主屏幕 - 编辑和改写"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self._build_ui()

    def _build_ui(self):
        self.clear_widgets()

        layout = MDBoxLayout(orientation='vertical', spacing=0)

        # ===== 顶部工具栏 =====
        toolbar = MDTopAppBar(
            title='论文降重助手',
            md_bg_color=self.theme_cls.primary_color,
            specific_text_color='#ffffff',
            left_action_items=[['menu', lambda x: self.app.open_drawer()]],
            right_action_items=[['cog-outline', lambda x: self.app.show_settings()]],
        )
        layout.add_widget(toolbar)

        # ===== 模式选择 =====
        mode_layout = MDBoxLayout(orientation='vertical', padding=[dp(12), dp(8), dp(12), dp(4)], size_hint_y=None, height=dp(70))

        self.mode_seg = MDSegmentedControl(
            on_active=lambda x: self._on_mode_change(),
        )
        self.mode_seg.add_widget(MDSegmentedControlItem(text='📄 全文'))
        self.mode_seg.add_widget(MDSegmentedControlItem(text='✂️ 选中'))
        self.mode_seg.add_widget(MDSegmentedControlItem(text='📋 报告'))
        mode_layout.add_widget(self.mode_seg)

        # 提示文字
        self.mode_hint = MDLabel(
            text='💡 粘贴全文，点击下方按钮一键降重',
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None, height=dp(20),
            padding=[dp(4), 0],
        )
        mode_layout.add_widget(self.mode_hint)
        layout.add_widget(mode_layout)

        # ===== 原文输入 =====
        self.input_field = MDTextField(
            mode='outlined',
            multiline=True,
            hint_text='粘贴或输入论文内容...',
            max_text_length=50000,
        )
        layout.add_widget(self.input_field)

        # ===== 改写按钮 =====
        btn_layout = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=dp(56),
            padding=[dp(12), dp(4), dp(12), dp(4)],
            spacing=dp(8),
        )

        self.rewrite_btn = MDRaisedButton(
            text='✏️ 开始降重',
            font_size=dp(16),
            size_hint_x=1,
            elevation=4,
            on_release=self._start_rewrite,
        )
        btn_layout.add_widget(self.rewrite_btn)

        layout.add_widget(btn_layout)

        # ===== 结果显示 =====
        self.result_card = MDCard(
            orientation='vertical',
            padding=[dp(12), dp(8)],
            size_hint_y=None,
            spacing=dp(6),
            md_bg_color=self.theme_cls.bg_darkest if self.theme_cls.theme_style == 'Dark' else '#f5f5f5',
        )

        self.result_label = MDLabel(text='', font_style='Body1')
        self.result_card.add_widget(self.result_label)

        # 评估行
        eval_layout = MDBoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=None, height=dp(40))
        self.eval_before = MDLabel(text='原文: --', font_style='Caption', halign='center')
        self.eval_arrow = MDLabel(text='➡', font_style='Caption', halign='center', size_hint_x=0.1)
        self.eval_after = MDLabel(text='改写后: --', font_style='Caption', halign='center')
        self.eval_reduction = MDLabel(text='', font_style='Caption', halign='center', bold=True)
        eval_layout.add_widget(self.eval_before)
        eval_layout.add_widget(self.eval_arrow)
        eval_layout.add_widget(self.eval_after)
        eval_layout.add_widget(self.eval_reduction)
        self.result_card.add_widget(eval_layout)

        self.result_card.bind(minimum_height=self.result_card.setter('height'))
        layout.add_widget(self.result_card)

        self.add_widget(layout)

    def _on_mode_change(self):
        """切换降重模式"""
        idx = self.mode_seg.get_active_item_index()
        hints = [
            '💡 粘贴全文，点击下方按钮一键降重',
            '✂️ 在原文中用手指选中文字，再点击改写',
            '📋 点击设置按钮 → 导入查重报告 → 自动匹配改写',
        ]
        self.mode_hint.text = hints[idx]
        self.result_card.opacity = 0.5 if idx > 0 else 1.0

    def _start_rewrite(self, *args):
        """开始改写"""
        idx = self.mode_seg.get_active_item_index()
        if idx == 0:
            self.app.rewrite_full()
        elif idx == 1:
            self.app.rewrite_selection()
        elif idx == 2:
            self.app.show_report_dialog()


# ==================== 设置屏幕 ====================

class SettingsScreen(MDScreen):
    """设置屏幕"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self._build_ui()

    def _build_ui(self):
        self.clear_widgets()
        layout = MDBoxLayout(orientation='vertical')

        toolbar = MDTopAppBar(
            title='设置',
            md_bg_color=self.theme_cls.primary_color,
            specific_text_color='#ffffff',
            left_action_items=[['arrow-left', lambda x: self.app.switch_screen('main')]],
        )
        layout.add_widget(toolbar)

        scroll = MDBoxLayout(orientation='vertical', padding=[dp(16), dp(8)], spacing=dp(12))

        # 语言选择
        scroll.add_widget(MDLabel(text='🌐 语言', font_style='Subtitle2'))
        self.lang_btn = MDSegmentedControl(size_hint_y=None, height=dp(36))
        self.lang_btn.add_widget(MDSegmentedControlItem(text='中文'))
        self.lang_btn.add_widget(MDSegmentedControlItem(text='English'))
        self.lang_btn.get_items()[0].active = True
        scroll.add_widget(self.lang_btn)

        # 改写力度
        scroll.add_widget(MDLabel(text='💪 改写力度', font_style='Subtitle2'))
        self.intensity_btn = MDSegmentedControl(size_hint_y=None, height=dp(36))
        self.intensity_btn.add_widget(MDSegmentedControlItem(text='轻'))
        self.intensity_btn.add_widget(MDSegmentedControlItem(text='中'))
        self.intensity_btn.add_widget(MDSegmentedControlItem(text='重'))
        self.intensity_btn.get_items()[1].active = True
        scroll.add_widget(self.intensity_btn)

        # 引擎选择
        scroll.add_widget(MDLabel(text='⚙️ 改写引擎', font_style='Subtitle2'))
        self.engine_btn = MDSegmentedControl(size_hint_y=None, height=dp(36))
        self.engine_btn.add_widget(MDSegmentedControlItem(text='本地引擎'))
        self.engine_btn.add_widget(MDSegmentedControlItem(text='AI增强'))
        self.engine_btn.get_items()[0].active = True
        scroll.add_widget(self.engine_btn)

        # API配置
        scroll.add_widget(MDLabel(text='🔑 API配置 (AI增强模式需要)', font_style='Subtitle2'))
        self.api_url = MDTextField(text='https://api.openai.com/v1', hint_text='API地址', mode='outlined')
        scroll.add_widget(self.api_url)
        self.api_key = MDTextField(hint_text='API密钥', mode='outlined', password=True)
        scroll.add_widget(self.api_key)
        self.api_model = MDTextField(text='gpt-4o-mini', hint_text='模型名', mode='outlined')
        scroll.add_widget(self.api_model)

        save_btn = MDRaisedButton(
            text='💾 保存设置',
            size_hint=(1, None), height=dp(48),
            on_release=self._save_settings,
        )
        scroll.add_widget(save_btn)

        # 查重报告导入区
        scroll.add_widget(MDLabel(text='📋 查重报告降重', font_style='Subtitle2'))
        scroll.add_widget(MDLabel(
            text='粘贴查重报告中的重复句子，每行一个',
            font_style='Caption', theme_text_color='Secondary',
        ))
        self.report_input = MDTextField(
            mode='outlined', multiline=True,
            hint_text='每行粘贴一个重复句子...',
            max_text_length=20000,
            size_hint_y=None, height=dp(150),
        )
        scroll.add_widget(self.report_input)

        report_btn = MDRaisedButton(
            text='🔍 查找并降重',
            size_hint=(1, None), height=dp(48),
            on_release=self._do_report_rewrite,
        )
        scroll.add_widget(report_btn)

        # 版本信息
        scroll.add_widget(MDLabel(
            text='\n\n论文降重助手 v1.0\n作者: onegod\n仅本地处理，数据安全',
            font_style='Caption', halign='center',
            theme_text_color='Hint',
        ))

        # 添加滚动
        from kivy.uix.scrollview import ScrollView
        sv = ScrollView()
        sv.add_widget(scroll)
        layout.add_widget(sv)
        self.add_widget(layout)

    def _save_settings(self, *args):
        """保存设置到app"""
        app = self.app
        app.lang = 'zh' if self.lang_btn.get_active_item_index() == 0 else 'en'
        intensities = ['light', 'medium', 'heavy']
        app.intensity = intensities[self.intensity_btn.get_active_item_index()]
        app.engine = 'local' if self.engine_btn.get_active_item_index() == 0 else 'api'

        api_key = self.api_key.text.strip()
        api_url = self.api_url.text.strip()
        model = self.api_model.text.strip()

        if api_key:
            app.api_rewriter.configure(
                api_key=api_key,
                api_url=api_url if api_url else 'https://api.openai.com/v1',
                model=model if model else 'gpt-4o-mini',
                temperature=0.8,
            )

        self.show_snackbar('✅ 设置已保存')

    def _do_report_rewrite(self, *args):
        """执行查重报告降重"""
        report_text = self.report_input.text.strip()
        if not report_text:
            self.show_snackbar('⚠️ 请先粘贴查重报告中的重复句子')
            return

        lines = [l.strip() for l in report_text.split('\n') if l.strip() and not l.strip().startswith('#')]
        if not lines:
            self.show_snackbar('⚠️ 未找到有效的句子')
            return

        self.app.rewrite_by_sentences(lines)

    def show_snackbar(self, text):
        MDSnackbar(text=text, y=dp(24)).open()


# ==================== APP主类 ====================

class PaperRewriterApp(MDApp):
    """论文降重助手 - 主应用"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = '论文降重助手'

        # 核心引擎
        self.local_rewriter = LocalRewriter()
        self.api_rewriter = ApiRewriter()

        # 设置状态
        self.lang = 'zh'
        self.intensity = 'medium'
        self.engine = 'local'

        # 屏幕引用
        self.main_screen = None
        self.settings_screen = None

    def build(self):
        """构建应用"""
        self.theme_cls.primary_palette = 'Blue'
        self.theme_cls.theme_style = 'Light'

        from kivy.uix.screenmanager import ScreenManager
        self.sm = ScreenManager()

        self.main_screen = MainScreen(name='main')
        self.settings_screen = SettingsScreen(name='settings')

        self.sm.add_widget(self.main_screen)
        self.sm.add_widget(self.settings_screen)

        return self.sm

    def switch_screen(self, name):
        """切换屏幕"""
        self.sm.current = name

    def open_drawer(self):
        """打开侧边菜单 - 显示模式提示"""
        from kivymd.uix.dialog import MDDialog
        dialog = MDDialog(
            title='关于',
            text='论文降重助手 v1.0\n\n'
                 '功能：\n'
                 '• 全文降重 - 一键改写整篇文章\n'
                 '• 选中降重 - 只改写选中的文字\n'
                 '• 查重降重 - 根据报告改写重复内容\n\n'
                 '作者: onegod\n'
                 '数据仅本地处理，安全可靠',
            buttons=[MDFlatButton(text='确定', on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()

    def show_settings(self):
        """打开设置"""
        self.switch_screen('settings')

    def show_report_dialog(self):
        """打开查重报告提示"""
        self.switch_screen('settings')
        MDSnackbar(text='📋 在设置页面下方粘贴查重报告句子', y=dp(24)).open()

    # ==================== 改写核心 ====================

    def rewrite_full(self):
        """全文改写"""
        text = self.main_screen.input_field.text.strip()
        if not text:
            MDSnackbar(text='⚠️ 请先输入需要降重的文本', y=dp(24)).open()
            return

        self._do_rewrite(text)

    def rewrite_selection(self):
        """选中改写"""
        try:
            field = self.main_screen.input_field
            sel_text = field.selection_text.strip()
            if not sel_text:
                MDSnackbar(text='✂️ 请先在原文中用手指选中文字', y=dp(24)).open()
                return

            full_text = field.text
            result = self._run_rewrite(sel_text)
            new_full = full_text.replace(sel_text, result, 1)

            field.text = new_full
            self._show_result(
                f'【选中改写完成】\n\n原文: {sel_text}\n\n改写: {result}',
                full_text, new_full
            )
        except Exception as e:
            MDSnackbar(text=f'❌ {str(e)}', y=dp(24)).open()

    def rewrite_by_sentences(self, sentences):
        """按查重报告句子改写"""
        full_text = self.main_screen.input_field.text.strip()
        if not full_text:
            MDSnackbar(text='⚠️ 原文为空，请先粘贴论文内容', y=dp(24)).open()
            return

        matched = []
        for s in sentences:
            if s in full_text:
                matched.append(s)
            else:
                # 模糊匹配
                clean_s = re.sub(r'[\s,，。、；：！？""（）《》【】\'\']', '', s)
                clean_f = re.sub(r'[\s,，。、；：！？""（）《》【】\'\']', '', full_text)
                if len(clean_s) >= 10 and clean_s in clean_f:
                    matched.append(s)

        if not matched:
            MDSnackbar(text='⚠️ 未在原文中找到匹配的重复句子', y=dp(24)).open()
            return

        def do_rewrite():
            result = full_text
            parts = []
            for i, sentence in enumerate(matched):
                new_text = self._run_rewrite(sentence)
                result = result.replace(sentence, new_text, 1)
                parts.append(f'【原文】{sentence}\n【改写】{new_text}')

            Clock.schedule_once(lambda dt: self._finish_report(full_text, result, parts, len(matched)))

        threading.Thread(target=do_rewrite, daemon=True).start()
        MDSnackbar(text=f'🔍 找到 {len(matched)} 处重复，正在改写...', y=dp(24)).open()

    def _finish_report(self, original, result, parts, count):
        """查重报告改写完成"""
        self.main_screen.input_field.text = result
        self._show_result(
            f'共改写 {count} 处重复内容\n\n' + '\n\n'.join(parts[:10]),
            original, result
        )
        MDSnackbar(text=f'✅ 查重降重完成，改写 {count} 处', y=dp(24)).open()

    # ==================== 通用改写逻辑 ====================

    def _do_rewrite(self, text):
        """执行改写"""
        def task():
            try:
                rewritten = self._run_rewrite(text)
                Clock.schedule_once(lambda dt: self._finish_rewrite(text, rewritten))
            except Exception as e:
                Clock.schedule_once(lambda dt: MDSnackbar(text=f'❌ {str(e)}', y=dp(24)).open())

        threading.Thread(target=task, daemon=True).start()
        MDSnackbar(text='✏️ 正在改写...', y=dp(24)).open()

    def _run_rewrite(self, text):
        """运行改写引擎"""
        strategies = ['synonym', 'pattern', 'voice', 'connector']

        if self.engine == 'api':
            if not self.api_rewriter.is_configured:
                raise Exception('API未配置，请在设置中填写API密钥')
            return self.api_rewriter.rewrite_sync(text, self.lang, self.intensity)
        else:
            result = self.local_rewriter.rewrite(text, self.lang, self.intensity, strategies)
            return result['text']

    def _finish_rewrite(self, original, rewritten):
        """改写完成"""
        self.main_screen.input_field.text = rewritten
        self._show_result(rewritten, original, rewritten)
        MDSnackbar(text='✅ 降重完成', y=dp(24)).open()

    def _show_result(self, display_text, original, rewritten):
        """显示结果和评估"""
        # 显示结果
        self.main_screen.result_label.text = display_text

        # 评估
        before = estimate_ai_probability(original, self.lang)
        after = estimate_ai_probability(rewritten, self.lang)

        b_score = before.get('overall', 0)
        a_score = after.get('overall', 0)

        self.main_screen.eval_before.text = f'原文: {b_score:.0f}%'
        self.main_screen.eval_after.text = f'改写后: {a_score:.0f}%'

        reduction = b_score - a_score
        if reduction > 0:
            self.main_screen.eval_reduction.text = f'降低 {reduction:.0f}%'
            self.main_screen.eval_reduction.theme_text_color = 'Custom'
            self.main_screen.eval_reduction.text_color = '#2e7d32'
        elif reduction < 0:
            self.main_screen.eval_reduction.text = f'升高 {abs(reduction):.0f}%'
            self.main_screen.eval_reduction.theme_text_color = 'Custom'
            self.main_screen.eval_reduction.text_color = '#c62828'
        else:
            self.main_screen.eval_reduction.text = '无变化'
            self.main_screen.eval_reduction.theme_text_color = 'Hint'

        # 展开结果卡片
        self.main_screen.result_card.opacity = 1


if __name__ == '__main__':
    PaperRewriterApp().run()
