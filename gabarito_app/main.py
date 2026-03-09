"""
Leitor de Cartão de Respostas CAEd
Prefeitura Municipal de Croatá — Secretaria de Educação
"""

import os
os.environ['KIVY_NO_ENV_CONFIG'] = '1'

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import StringProperty, ListProperty, ObjectProperty

import threading
from datetime import datetime

from utils.card_reader import CardReader
from utils.excel_exporter import ExcelExporter


# ── Paleta de cores ────────────────────────────────────────────────────────────
C_DARK_BLUE  = get_color_from_hex('#1F4E79')
C_BLUE       = get_color_from_hex('#2E75B6')
C_LIGHT_BLUE = get_color_from_hex('#9DC3E6')
C_ORANGE     = get_color_from_hex('#ED7D31')
C_LIGHT_ORG  = get_color_from_hex('#F8CBAD')
C_WHITE      = get_color_from_hex('#FFFFFF')
C_GRAY       = get_color_from_hex('#F2F2F2')
C_TEXT_GRAY  = get_color_from_hex('#999999')
C_RED        = get_color_from_hex('#C00000')
C_YELLOW     = get_color_from_hex('#FFD700')
C_BG         = get_color_from_hex('#F0F4F8')


def make_btn(text, bg_color, text_color=C_WHITE, font_size=16, height=dp(50), **kwargs):
    btn = Button(
        text=text,
        size_hint_y=None,
        height=height,
        font_size=dp(font_size),
        background_normal='',
        background_color=bg_color,
        color=text_color,
        bold=True,
        **kwargs
    )
    return btn


# ── Tela Inicial ───────────────────────────────────────────────────────────────
class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*C_BG)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)
        self._build()

    def _update_rect(self, *a):
        self.rect.size = self.size
        self.rect.pos = self.pos

    def _build(self):
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))

        # Header
        header = BoxLayout(size_hint_y=None, height=dp(100),
                           orientation='vertical', padding=dp(10))
        with header.canvas.before:
            Color(*C_DARK_BLUE)
            self.hdr_rect = RoundedRectangle(size=header.size, pos=header.pos, radius=[dp(12)])
        header.bind(size=lambda i, v: setattr(self.hdr_rect, 'size', v),
                    pos=lambda i, v: setattr(self.hdr_rect, 'pos', v))

        header.add_widget(Label(
            text='📋 Leitor de Gabarito CAEd',
            font_size=dp(18), bold=True, color=C_WHITE,
            size_hint_y=None, height=dp(40)
        ))
        header.add_widget(Label(
            text='Prefeitura Municipal de Croatá',
            font_size=dp(12), color=C_LIGHT_BLUE,
            size_hint_y=None, height=dp(25)
        ))
        layout.add_widget(header)

        # Ícone central
        layout.add_widget(Label(
            text='📷', font_size=dp(80),
            size_hint_y=None, height=dp(120)
        ))

        layout.add_widget(Label(
            text='Posicione o cartão de respostas\nna frente da câmera e capture',
            font_size=dp(14), color=C_DARK_BLUE,
            halign='center', size_hint_y=None, height=dp(60)
        ))

        # Botões principais
        btn_camera = make_btn('📷  Capturar Cartão', C_BLUE, height=dp(60), font_size=18)
        btn_camera.bind(on_press=lambda x: self._go('camera'))
        layout.add_widget(btn_camera)

        btn_history = make_btn('📁  Ver Resultados Salvos', C_DARK_BLUE, height=dp(55))
        btn_history.bind(on_press=lambda x: self._go('history'))
        layout.add_widget(btn_history)

        # Info blocos
        info = GridLayout(cols=2, size_hint_y=None, height=dp(80), spacing=dp(8))
        for label, color in [
            ('Bloco 01 & 03\nLíngua Portuguesa', C_BLUE),
            ('Bloco 02 & 04\nMatemática', C_ORANGE)
        ]:
            box = BoxLayout()
            with box.canvas.before:
                Color(*color)
                r = RoundedRectangle(size=box.size, pos=box.pos, radius=[dp(8)])
            box.bind(size=lambda i, v, rr=r: setattr(rr, 'size', v),
                     pos=lambda i, v, rr=r: setattr(rr, 'pos', v))
            box.add_widget(Label(text=label, font_size=dp(11),
                                 color=C_WHITE, halign='center', bold=True))
            info.add_widget(box)
        layout.add_widget(info)

        layout.add_widget(Label())  # spacer
        self.add_widget(layout)

    def _go(self, screen):
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = screen


# ── Tela da Câmera ─────────────────────────────────────────────────────────────
class CameraScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        layout = BoxLayout(orientation='vertical')

        # Toolbar
        toolbar = BoxLayout(size_hint_y=None, height=dp(55), padding=dp(8))
        with toolbar.canvas.before:
            Color(*C_DARK_BLUE)
            self.tb_rect = Rectangle(size=toolbar.size, pos=toolbar.pos)
        toolbar.bind(size=lambda i, v: setattr(self.tb_rect, 'size', v),
                     pos=lambda i, v: setattr(self.tb_rect, 'pos', v))

        btn_back = Button(text='← Voltar', size_hint_x=None, width=dp(90),
                          background_normal='', background_color=(0, 0, 0, 0),
                          color=C_WHITE, font_size=dp(14))
        btn_back.bind(on_press=lambda x: self._go_back())
        toolbar.add_widget(btn_back)
        toolbar.add_widget(Label(text='Capturar Cartão', color=C_WHITE,
                                 font_size=dp(16), bold=True))
        layout.add_widget(toolbar)

        # Câmera
        self.camera = Camera(index=0, resolution=(1280, 960), play=False)
        layout.add_widget(self.camera)

        # Guia de enquadramento
        guide = Label(
            text='[Alinhe o cartão dentro da área visível]',
            font_size=dp(12), color=C_YELLOW,
            size_hint_y=None, height=dp(30)
        )
        layout.add_widget(guide)

        # Botão capturar
        btn_cap = make_btn('📸  Fotografar e Analisar', C_ORANGE,
                           height=dp(65), font_size=18)
        btn_cap.bind(on_press=self._capture)
        layout.add_widget(btn_cap)

        self.status_label = Label(text='', font_size=dp(13),
                                  color=C_TEXT_GRAY, size_hint_y=None, height=dp(30))
        layout.add_widget(self.status_label)

        self.add_widget(layout)

    def on_enter(self):
        self.camera.play = True

    def on_leave(self):
        self.camera.play = False

    def _go_back(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'home'

    def _capture(self, *a):
        self.status_label.text = '⏳ Analisando cartão...'
        self.status_label.color = C_YELLOW

        # Salva frame temporário
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = f'/sdcard/gabarito_temp_{timestamp}.png'
        try:
            self.camera.export_to_png(path)
        except Exception:
            path = f'/tmp/gabarito_temp_{timestamp}.png'
            self.camera.export_to_png(path)

        threading.Thread(target=self._process, args=(path,), daemon=True).start()

    def _process(self, path):
        reader = CardReader()
        result = reader.process_image(path)
        Clock.schedule_once(lambda dt: self._show_result(result, path), 0)

    def _show_result(self, result, img_path):
        if result['success']:
            self.status_label.text = '✅ Cartão lido com sucesso!'
            self.status_label.color = get_color_from_hex('#00AA00')
            # Passa dados para tela de resultado
            rs = self.manager.get_screen('result')
            rs.set_data(result, img_path)
            Clock.schedule_once(lambda dt: self._go_result(), 0.5)
        else:
            self.status_label.text = f'❌ {result["error"]}'
            self.status_label.color = C_RED

    def _go_result(self):
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = 'result'


# ── Tela de Resultado ──────────────────────────────────────────────────────────
class ResultScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.result_data = {}
        self.img_path = ''
        self._build()

    def _build(self):
        self.main_layout = BoxLayout(orientation='vertical')

        # Toolbar
        toolbar = BoxLayout(size_hint_y=None, height=dp(55), padding=dp(8))
        with toolbar.canvas.before:
            Color(*C_DARK_BLUE)
            r = Rectangle(size=toolbar.size, pos=toolbar.pos)
        toolbar.bind(size=lambda i, v: setattr(r, 'size', v),
                     pos=lambda i, v: setattr(r, 'pos', v))

        btn_back = Button(text='← Nova Leitura', size_hint_x=None, width=dp(130),
                          background_normal='', background_color=(0, 0, 0, 0),
                          color=C_WHITE, font_size=dp(13))
        btn_back.bind(on_press=lambda x: self._new_capture())
        toolbar.add_widget(btn_back)
        toolbar.add_widget(Label(text='Resultado', color=C_WHITE,
                                 font_size=dp(16), bold=True))
        self.main_layout.add_widget(toolbar)

        # Info do aluno
        self.student_box = BoxLayout(size_hint_y=None, height=dp(60),
                                     padding=(dp(15), dp(8)))
        with self.student_box.canvas.before:
            Color(*C_BLUE)
            r2 = Rectangle(size=self.student_box.size, pos=self.student_box.pos)
        self.student_box.bind(size=lambda i, v: setattr(r2, 'size', v),
                              pos=lambda i, v: setattr(r2, 'pos', v))
        self.student_label = Label(text='Aluno: —', font_size=dp(13),
                                   color=C_WHITE, bold=True, halign='left')
        self.student_box.add_widget(self.student_label)
        self.main_layout.add_widget(self.student_box)

        # Scroll com respostas
        scroll = ScrollView()
        self.answers_grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(6),
                                       padding=dp(10))
        self.answers_grid.bind(minimum_height=self.answers_grid.setter('height'))
        scroll.add_widget(self.answers_grid)
        self.main_layout.add_widget(scroll)

        # Botões de ação
        btn_row = BoxLayout(size_hint_y=None, height=dp(60),
                            spacing=dp(10), padding=dp(10))
        btn_export = make_btn('📊 Exportar Excel', C_ORANGE, height=dp(50), font_size=15)
        btn_export.bind(on_press=self._export_excel)
        btn_edit = make_btn('✏️ Corrigir', C_BLUE, height=dp(50), font_size=15)
        btn_edit.bind(on_press=self._edit_mode)
        btn_row.add_widget(btn_edit)
        btn_row.add_widget(btn_export)
        self.main_layout.add_widget(btn_row)

        self.add_widget(self.main_layout)

    def set_data(self, result, img_path):
        self.result_data = result
        self.img_path = img_path
        self._render()

    def _render(self):
        self.answers_grid.clear_widgets()
        data = self.result_data

        nome = data.get('student_name', 'Não identificado')
        self.student_label.text = f'👤  {nome}'

        blocks = [
            ('Bloco 01 — Língua Portuguesa', range(1, 14),  C_BLUE,   C_LIGHT_BLUE),
            ('Bloco 02 — Matemática',        range(14, 27), C_ORANGE, C_LIGHT_ORG),
            ('Bloco 03 — Língua Portuguesa', range(27, 40), C_BLUE,   C_LIGHT_BLUE),
            ('Bloco 04 — Matemática',        range(40, 53), C_ORANGE, C_LIGHT_ORG),
        ]

        answers = data.get('answers', {})

        for block_name, q_range, header_color, cell_color in blocks:
            # Header do bloco
            hdr = BoxLayout(size_hint_y=None, height=dp(32), padding=(dp(10), dp(4)))
            with hdr.canvas.before:
                Color(*header_color)
                r = RoundedRectangle(size=hdr.size, pos=hdr.pos, radius=[dp(6)])
            hdr.bind(size=lambda i, v, rr=r: setattr(rr, 'size', v),
                     pos=lambda i, v, rr=r: setattr(rr, 'pos', v))
            hdr.add_widget(Label(text=block_name, color=C_WHITE,
                                 font_size=dp(12), bold=True))
            self.answers_grid.add_widget(hdr)

            # Grid de respostas (4 por linha)
            row_grid = GridLayout(cols=4, size_hint_y=None,
                                  height=dp(40) * -(-len(list(q_range)) // 4),
                                  spacing=dp(4))

            for q in q_range:
                val = answers.get(q, 'NR')
                cell = self._make_answer_cell(q, val, cell_color)
                row_grid.add_widget(cell)

            self.answers_grid.add_widget(row_grid)

    def _make_answer_cell(self, q_num, val, bg_color):
        box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(50),
                        padding=dp(3))

        if val == 'NR':
            bg = get_color_from_hex('#E8E8E8')
            fc = C_TEXT_GRAY
        elif val == 'NULA':
            bg = C_RED
            fc = C_WHITE
        elif val == '?':
            bg = C_YELLOW
            fc = get_color_from_hex('#333333')
        else:
            bg = bg_color
            fc = C_DARK_BLUE

        with box.canvas.before:
            Color(*bg)
            r = RoundedRectangle(size=box.size, pos=box.pos, radius=[dp(5)])
        box.bind(size=lambda i, v, rr=r: setattr(rr, 'size', v),
                 pos=lambda i, v, rr=r: setattr(rr, 'pos', v))

        box.add_widget(Label(text=f'Q{q_num:02d}', font_size=dp(9),
                             color=get_color_from_hex('#666666'),
                             size_hint_y=None, height=dp(16)))
        box.add_widget(Label(text=val, font_size=dp(16), bold=True,
                             color=fc))
        return box

    def _export_excel(self, *a):
        exporter = ExcelExporter()
        try:
            path = exporter.export(self.result_data)
            self._popup('✅ Exportado!',
                        f'Arquivo salvo em:\n{path}',
                        C_BLUE)
        except Exception as e:
            self._popup('❌ Erro', str(e), C_RED)

    def _edit_mode(self, *a):
        self.manager.transition = SlideTransition(direction='left')
        es = self.manager.get_screen('edit')
        es.set_data(self.result_data)
        self.manager.current = 'edit'

    def _popup(self, title, msg, color):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        content.add_widget(Label(text=msg, font_size=dp(14),
                                 halign='center', color=C_DARK_BLUE))
        btn = make_btn('OK', color, height=dp(45))
        pop = Popup(title=title, content=content,
                    size_hint=(0.85, 0.4), auto_dismiss=True)
        btn.bind(on_press=pop.dismiss)
        content.add_widget(btn)
        pop.open()

    def _new_capture(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'camera'


# ── Tela de Edição Manual ──────────────────────────────────────────────────────
class EditScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = {}
        self.btn_map = {}   # (q_num) -> list of 4 buttons
        self._build()

    def _build(self):
        layout = BoxLayout(orientation='vertical')

        toolbar = BoxLayout(size_hint_y=None, height=dp(55), padding=dp(8))
        with toolbar.canvas.before:
            Color(*C_DARK_BLUE)
            r = Rectangle(size=toolbar.size, pos=toolbar.pos)
        toolbar.bind(size=lambda i, v: setattr(r, 'size', v),
                     pos=lambda i, v: setattr(r, 'pos', v))
        btn_back = Button(text='← Cancelar', size_hint_x=None, width=dp(110),
                          background_normal='', background_color=(0, 0, 0, 0),
                          color=C_WHITE, font_size=dp(13))
        btn_back.bind(on_press=self._cancel)
        toolbar.add_widget(btn_back)
        toolbar.add_widget(Label(text='Corrigir Respostas', color=C_WHITE,
                                 font_size=dp(16), bold=True))
        btn_save = Button(text='Salvar ✓', size_hint_x=None, width=dp(90),
                          background_normal='', background_color=(0, 0, 0, 0),
                          color=C_YELLOW, font_size=dp(14), bold=True)
        btn_save.bind(on_press=self._save)
        toolbar.add_widget(btn_save)
        layout.add_widget(toolbar)

        scroll = ScrollView()
        self.grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4), padding=dp(8))
        self.grid.bind(minimum_height=self.grid.setter('height'))
        scroll.add_widget(self.grid)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def set_data(self, data):
        self.data = {k: v for k, v in data.items()}
        self.data['answers'] = dict(data.get('answers', {}))
        self._render()

    def _render(self):
        self.grid.clear_widgets()
        self.btn_map = {}
        answers = self.data.get('answers', {})

        blocks = [
            ('Bloco 01 — LP',  range(1, 14),  C_BLUE),
            ('Bloco 02 — Mat', range(14, 27), C_ORANGE),
            ('Bloco 03 — LP',  range(27, 40), C_BLUE),
            ('Bloco 04 — Mat', range(40, 53), C_ORANGE),
        ]

        for block_name, q_range, color in blocks:
            hdr = BoxLayout(size_hint_y=None, height=dp(28), padding=(dp(8), dp(2)))
            with hdr.canvas.before:
                Color(*color)
                r = Rectangle(size=hdr.size, pos=hdr.pos)
            hdr.bind(size=lambda i, v, rr=r: setattr(rr, 'size', v),
                     pos=lambda i, v, rr=r: setattr(rr, 'pos', v))
            hdr.add_widget(Label(text=block_name, color=C_WHITE,
                                 font_size=dp(11), bold=True))
            self.grid.add_widget(hdr)

            for q in q_range:
                row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(5),
                                padding=(dp(5), dp(3)))
                row.add_widget(Label(text=f'Q{q:02d}', size_hint_x=None,
                                     width=dp(38), font_size=dp(12),
                                     bold=True, color=C_DARK_BLUE))
                btns = []
                current = answers.get(q, 'NR')
                for opt in ['A', 'B', 'C', 'D', 'NR']:
                    active = (current == opt)
                    bg = color if active else get_color_from_hex('#DDDDDD')
                    fc = C_WHITE if active else C_DARK_BLUE
                    b = Button(text=opt, font_size=dp(12), bold=active,
                               background_normal='', background_color=bg,
                               color=fc)
                    b.bind(on_press=lambda inst, qq=q, oo=opt: self._select(qq, oo))
                    btns.append(b)
                    row.add_widget(b)
                self.btn_map[q] = btns
                self.grid.add_widget(row)

    def _select(self, q_num, option):
        self.data['answers'][q_num] = option
        opts = ['A', 'B', 'C', 'D', 'NR']
        block_q = q_num
        disc_color = C_BLUE if (1 <= block_q <= 13 or 27 <= block_q <= 39) else C_ORANGE
        for i, btn in enumerate(self.btn_map[q_num]):
            active = (opts[i] == option)
            btn.background_color = disc_color if active else get_color_from_hex('#DDDDDD')
            btn.color = C_WHITE if active else C_DARK_BLUE
            btn.bold = active

    def _save(self, *a):
        rs = self.manager.get_screen('result')
        rs.set_data(self.data, rs.img_path)
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'result'

    def _cancel(self, *a):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'result'


# ── Tela de Histórico ──────────────────────────────────────────────────────────
class HistoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        layout = BoxLayout(orientation='vertical')

        toolbar = BoxLayout(size_hint_y=None, height=dp(55), padding=dp(8))
        with toolbar.canvas.before:
            Color(*C_DARK_BLUE)
            r = Rectangle(size=toolbar.size, pos=toolbar.pos)
        toolbar.bind(size=lambda i, v: setattr(r, 'size', v),
                     pos=lambda i, v: setattr(r, 'pos', v))
        btn_back = Button(text='← Voltar', size_hint_x=None, width=dp(90),
                          background_normal='', background_color=(0, 0, 0, 0),
                          color=C_WHITE, font_size=dp(14))
        btn_back.bind(on_press=lambda x: self._go_home())
        toolbar.add_widget(btn_back)
        toolbar.add_widget(Label(text='Resultados Salvos', color=C_WHITE,
                                 font_size=dp(16), bold=True))
        layout.add_widget(toolbar)

        scroll = ScrollView()
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None,
                                     spacing=dp(6), padding=dp(10))
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll.add_widget(self.list_layout)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def on_enter(self):
        self._load_files()

    def _load_files(self):
        self.list_layout.clear_widgets()
        base = self._get_save_dir()
        files = sorted(
            [f for f in os.listdir(base) if f.endswith('.xlsx')],
            reverse=True
        ) if os.path.exists(base) else []

        if not files:
            self.list_layout.add_widget(Label(
                text='Nenhum arquivo salvo ainda.',
                color=C_TEXT_GRAY, font_size=dp(14),
                size_hint_y=None, height=dp(60)
            ))
            return

        for fname in files:
            row = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(8))
            with row.canvas.before:
                Color(*C_WHITE)
                r = RoundedRectangle(size=row.size, pos=row.pos, radius=[dp(8)])
            row.bind(size=lambda i, v, rr=r: setattr(rr, 'size', v),
                     pos=lambda i, v, rr=r: setattr(rr, 'pos', v))
            row.add_widget(Label(text=f'📊 {fname}', font_size=dp(11),
                                 color=C_DARK_BLUE, halign='left'))
            self.list_layout.add_widget(row)

    def _get_save_dir(self):
        try:
            from android.storage import primary_external_storage_path
            return os.path.join(primary_external_storage_path(), 'GabaritoCAEd')
        except Exception:
            return os.path.join(os.path.expanduser('~'), 'GabaritoCAEd')

    def _go_home(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'home'


# ── App Principal ──────────────────────────────────────────────────────────────
class GabaritoApp(App):
    def build(self):
        Window.clearcolor = (*C_BG, 1)
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(CameraScreen(name='camera'))
        sm.add_widget(ResultScreen(name='result'))
        sm.add_widget(EditScreen(name='edit'))
        sm.add_widget(HistoryScreen(name='history'))
        return sm

    def get_application_name(self):
        return 'Gabarito CAEd'


if __name__ == '__main__':
    GabaritoApp().run()
