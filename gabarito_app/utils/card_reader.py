"""
CardReader — Leitura do Cartão de Respostas CAEd via OpenCV

Fluxo:
1. Carrega a imagem
2. Detecta e corrige perspectiva do cartão (homografia)
3. Localiza as 4 grades de blocos por regiões fixas (layout fixo CAEd)
4. Para cada questão, analisa as 4 bolinhas e determina qual está marcada
5. Retorna dicionário com respostas Q1..Q52
"""

import cv2
import numpy as np


# ── Constantes de layout (proporções do cartão normalizado 1000×1414) ──────────
CARD_W = 1000
CARD_H = 1414

# Cada bloco: (x_start, y_start, x_end, y_end) em proporção 0..1
# Ajustados empiricamente ao layout CAEd Croatá
BLOCK_REGIONS = {
    'B01': (0.03, 0.38, 0.28, 0.88),   # Bloco 01 LP  Q01-Q13
    'B02': (0.28, 0.38, 0.53, 0.88),   # Bloco 02 Mat Q14-Q26
    'B03': (0.53, 0.38, 0.77, 0.88),   # Bloco 03 LP  Q27-Q39
    'B04': (0.77, 0.38, 1.00, 0.88),   # Bloco 04 Mat Q40-Q52
}

QUESTIONS_PER_BLOCK = 13
OPTIONS = 4  # A B C D


class CardReader:

    def process_image(self, image_path: str) -> dict:
        """
        Processa a imagem do cartão e retorna:
        {
            'success': bool,
            'student_name': str,
            'answers': {1: 'A', 2: 'NR', ...},
            'flags': {q: 'NULA'|'?'},
            'error': str (se success=False)
        }
        """
        img = cv2.imread(image_path)
        if img is None:
            return {'success': False, 'error': 'Não foi possível abrir a imagem.'}

        # 1. Pré-processamento
        img = self._auto_rotate(img)

        # 2. Detectar e retificar o cartão
        card = self._detect_and_warp(img)
        if card is None:
            # Fallback: usa a imagem inteira redimensionada
            card = cv2.resize(img, (CARD_W, CARD_H))

        # 3. Ler nome do aluno (OCR simples por posição — retorna placeholder)
        student_name = self._read_student_name(card)

        # 4. Ler respostas
        answers, flags = self._read_all_blocks(card)

        return {
            'success': True,
            'student_name': student_name,
            'answers': answers,
            'flags': flags,
        }

    # ── Pré-processamento ──────────────────────────────────────────────────────

    def _auto_rotate(self, img):
        """Corrige orientação se a imagem estiver deitada."""
        h, w = img.shape[:2]
        if w > h:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        return img

    # ── Detecção de perspectiva ────────────────────────────────────────────────

    def _detect_and_warp(self, img):
        """Detecta o retângulo do cartão e corrige a perspectiva."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 30, 120)

        # Dilata para fechar bordas
        kernel = np.ones((3, 3), np.uint8)
        edged = cv2.dilate(edged, kernel, iterations=2)

        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        card_contour = None
        for cnt in contours[:10]:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4:
                area = cv2.contourArea(approx)
                img_area = img.shape[0] * img.shape[1]
                if area > img_area * 0.3:
                    card_contour = approx
                    break

        if card_contour is None:
            return None

        pts = card_contour.reshape(4, 2).astype(np.float32)
        pts = self._order_points(pts)

        dst = np.array([
            [0, 0],
            [CARD_W - 1, 0],
            [CARD_W - 1, CARD_H - 1],
            [0, CARD_H - 1]
        ], dtype=np.float32)

        M = cv2.getPerspectiveTransform(pts, dst)
        warped = cv2.warpPerspective(img, M, (CARD_W, CARD_H))
        return warped

    def _order_points(self, pts):
        """Ordena: topo-esquerda, topo-direita, baixo-direita, baixo-esquerda."""
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    # ── Leitura das respostas ──────────────────────────────────────────────────

    def _read_all_blocks(self, card):
        answers = {}
        flags = {}

        block_qs = {
            'B01': range(1, 14),
            'B02': range(14, 27),
            'B03': range(27, 40),
            'B04': range(40, 53),
        }

        for block_key, q_range in block_qs.items():
            region = BLOCK_REGIONS[block_key]
            block_answers = self._read_block(card, region, len(list(q_range)))

            for i, q in enumerate(q_range):
                val = block_answers[i] if i < len(block_answers) else 'NR'
                if val == 'NULA':
                    flags[q] = 'NULA'
                    answers[q] = 'NULA'
                elif val == '?':
                    flags[q] = '?'
                    answers[q] = '?'
                else:
                    answers[q] = val

        return answers, flags

    def _read_block(self, card, region, num_questions):
        """Lê um bloco do cartão e retorna lista de respostas."""
        x1 = int(region[0] * CARD_W)
        y1 = int(region[1] * CARD_H)
        x2 = int(region[2] * CARD_W)
        y2 = int(region[3] * CARD_H)

        block_img = card[y1:y2, x1:x2]
        bh, bw = block_img.shape[:2]

        # Converte para escala de cinza e binariza
        gray = cv2.cvtColor(block_img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255,
                                   cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Altura de cada linha de questão
        row_h = bh / num_questions
        # Largura de cada bolinha (4 colunas)
        col_w = bw / OPTIONS

        results = []
        for q_idx in range(num_questions):
            y_start = int(q_idx * row_h)
            y_end = int((q_idx + 1) * row_h)

            filled = []
            densities = []
            for opt_idx in range(OPTIONS):
                x_start = int(opt_idx * col_w)
                x_end = int((opt_idx + 1) * col_w)

                # Recorta a célula da bolinha com margem
                margin_x = int(col_w * 0.15)
                margin_y = int(row_h * 0.15)
                cell = thresh[
                    y_start + margin_y: y_end - margin_y,
                    x_start + margin_x: x_end - margin_x
                ]

                if cell.size == 0:
                    densities.append(0)
                    continue

                # Densidade de pixels brancos (invertidos) = pixels escuros originais
                density = np.sum(cell > 0) / cell.size
                densities.append(density)

            # Threshold adaptativo: marcado se density > 0.18
            MARK_THRESHOLD = 0.18
            marked = [d > MARK_THRESHOLD for d in densities]
            num_marked = sum(marked)

            if num_marked == 0:
                results.append('NR')
            elif num_marked == 1:
                results.append(['A', 'B', 'C', 'D'][marked.index(True)])
            elif num_marked >= 2:
                # Verifica se há uma dominante clara
                max_d = max(densities)
                others = [d for d in densities if d != max_d]
                if max_d > 2.5 * max(others, default=0):
                    results.append(['A', 'B', 'C', 'D'][densities.index(max_d)])
                else:
                    results.append('NULA')

        return results

    # ── Nome do aluno ──────────────────────────────────────────────────────────

    def _read_student_name(self, card):
        """
        Tenta ler o nome via OCR (pytesseract se disponível).
        Fallback: retorna placeholder para preenchimento manual.
        """
        try:
            import pytesseract
            # Recorta a região do nome (proporção CAEd)
            x1, y1 = int(0.03 * CARD_W), int(0.17 * CARD_H)
            x2, y2 = int(0.97 * CARD_W), int(0.26 * CARD_H)
            name_region = card[y1:y2, x1:x2]
            gray = cv2.cvtColor(name_region, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255,
                                       cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(
                thresh,
                config='--psm 7 -l por'
            ).strip().upper()
            return text if len(text) > 3 else 'IDENTIFICAR MANUALMENTE'
        except Exception:
            return 'IDENTIFICAR MANUALMENTE'
