from PIL import Image, ImageDraw, ImageFont
import os
import re
from datetime import datetime
import platform

class ReportGenerator:
    def __init__(self):
        self.template_dir = 'templates/'
        self.output_dir = 'share_cache/'
        self.cache_paths = {}
        
        os.makedirs(self.template_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        self._load_fonts()
    
    def _get_font_path(self):
        system = platform.system()
        if system == "Windows":
            return "C:/Windows/Fonts/arial.ttf"
        elif system == "Linux":
            paths = ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"]
            for p in paths:
                if os.path.exists(p):
                    return p
            return None
        elif system == "Darwin":
            return "/System/Library/Fonts/Arial.ttf"
        return None
    
    def _load_fonts(self):
        font_path = self._get_font_path()
        if font_path and os.path.exists(font_path):
            self.font_title = ImageFont.truetype(font_path, 48)
            self.font_large = ImageFont.truetype(font_path, 56)
            self.font_medium = ImageFont.truetype(font_path, 32)
            self.font_small = ImageFont.truetype(font_path, 24)
            self.font_tiny = ImageFont.truetype(font_path, 18)
            self.font_mini = ImageFont.truetype(font_path, 14)
            print(f"Шрифт загружен: {font_path}")
        else:
            self.font_title = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()
            self.font_mini = ImageFont.load_default()
            print("Шрифт не найден, используется стандартный")
    
    def wrap_text(self, text, max_length=20):
        if not text:
            return text
        words = re.split(r'(\s+|-)', text)
        lines = []
        current_line = ""
        for word in words:
            if len(current_line + word) <= max_length:
                current_line += word
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word
        if current_line:
            lines.append(current_line.strip())
        return '\n'.join(lines)
    
    def draw_wrapped_text_in_rect(self, draw, text, rect, font, fill, padding=20):
        if not text:
            return 0
        x1, y1, x2, y2 = rect
        inner_width = (x2 - x1) - 2 * padding
        center_x = (x1 + x2) // 2
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= inner_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        if not lines:
            return 0
        line_height = draw.textbbox((0, 0), "A", font=font)[3] + 5
        total_height = len(lines) * line_height
        start_y = y1 + (y2 - y1 - total_height) // 2
        for line in lines:
            draw.text((center_x, start_y), line, fill=fill, font=font, anchor='mt')
            start_y += line_height
        return total_height
    
    def draw_text_in_rect(self, draw, text, rect, font, fill):
        x1, y1, x2, y2 = rect
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        max_width = (x2 - x1) - 20
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width > max_width:
            for size in range(24, 10, -2):
                try:
                    font_path = self._get_font_path()
                    smaller_font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
                except:
                    smaller_font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), text, font=smaller_font)
                if bbox[2] - bbox[0] <= max_width:
                    draw.text((center_x, center_y), text, fill=fill, font=smaller_font, anchor='mm')
                    return
            draw.text((center_x, center_y), text, fill=fill, font=font, anchor='mm')
        else:
            draw.text((center_x, center_y), text, fill=fill, font=font, anchor='mm')
    
    def calculate_dino_location(self, total_tasks, avg_score, homework_completion):
        xp = (total_tasks * 2) + (avg_score * 3) + (homework_completion * 1)
        if xp < 100:
            return 0, "Опушка леса", xp
        elif xp < 300:
            return 1, "Тропинка", xp
        elif xp < 600:
            return 2, "Поляна", xp
        elif xp < 1000:
            return 3, "Ручей", xp
        elif xp < 1500:
            return 4, "Болото", xp
        elif xp < 2100:
            return 5, "Пещера дракона", xp
        else:
            return 6, "Солнце", xp
    
    def get_achievements(self, student_data):
        total_tasks = student_data.get('total_tasks', 0)
        avg_score = student_data.get('avg_score', 0)
        homework_completion = student_data.get('homework_completion', 0)
        
        achievements = []
        if avg_score > 85:
            achievements.append("Отличные баллы!")
        if homework_completion > 90:
            achievements.append("Почти все задания выполнены!")
        if total_tasks > 100:
            achievements.append("Решено много задач!")
        if total_tasks < 50:
            achievements.append("Ты в начале пути!")
        if not achievements:
            achievements.append("Продолжай в том же духе!")
        return achievements
    
    def generate_report(self, student_data, age_group='senior', period_name=''):
        if age_group == 'primary':
            return self._generate_primary_report(student_data, period_name)
        else:
            return self._generate_senior_report(student_data, period_name)
    
    def _generate_senior_report(self, student_data, period_name):
        img = Image.new('RGB', (1200, 1700), color='#0F172A')
        draw = ImageDraw.Draw(img)
        
        student_id = student_data.get('id', 'unknown')
        name = f"Ученик {student_id}"
        grade = student_data.get('grade', 10)
        total_tasks = student_data.get('total_tasks', 0)
        avg_score = student_data.get('avg_score', 0)
        homework_completion = student_data.get('homework_completion', 0)
        
        achievements = self.get_achievements(student_data)
        
        self.draw_wrapped_text_in_rect(draw, name, [200, 40, 1000, 100], self.font_title, '#F1F5F9', 20)
        self.draw_wrapped_text_in_rect(draw, f"{grade} класс", [200, 110, 1000, 160], self.font_medium, '#94A3B8', 20)
        self.draw_wrapped_text_in_rect(draw, "ИТОГОВЫЙ ОТЧЁТ", [200, 170, 1000, 220], self.font_medium, '#F97316', 20)
        
        for x in [200, 600, 1000]:
            draw.rectangle([x-150, 280, x+150, 520], fill='#1E293B', outline='#38BDF8', width=3)
        
        self.draw_text_in_rect(draw, str(total_tasks), [50, 280, 350, 400], self.font_large, '#38BDF8')
        self.draw_text_in_rect(draw, "решённых задач", [50, 400, 350, 480], self.font_small, '#94A3B8')
        
        self.draw_text_in_rect(draw, str(avg_score), [450, 280, 750, 400], self.font_large, '#38BDF8')
        self.draw_text_in_rect(draw, "средний балл (%)", [450, 400, 750, 480], self.font_small, '#94A3B8')
        
        self.draw_text_in_rect(draw, f"{homework_completion}%", [850, 280, 1150, 400], self.font_large, '#38BDF8')
        self.draw_text_in_rect(draw, "выполнение ДЗ", [850, 400, 1150, 480], self.font_small, '#94A3B8')
        
        if achievements:
            self.draw_wrapped_text_in_rect(draw, "ТВОИ ДОСТИЖЕНИЯ", [200, 570, 1000, 630], self.font_medium, '#F97316', 20)
            y_ach = 650
            for ach in achievements:
                self.draw_wrapped_text_in_rect(draw, ach, [200, y_ach-20, 1000, y_ach+30], self.font_small, '#FFD700', 20)
                y_ach += 50
        
        universal_text = "Каждый урок приближает тебя к цели. Не останавливайся!\n\nПродолжая в том же темпе, ты можешь достичь больших успехов\nв любой сфере, которая тебе по душе"
        
        draw.rectangle([200, 780, 1000, 1000], fill='#FEF3C7', outline='#F97316', width=2)
        self.draw_wrapped_text_in_rect(draw, universal_text, [200, 780, 1000, 1000], self.font_medium, '#92400E', 25)
        
        self.draw_wrapped_text_in_rect(draw, f"{datetime.now().strftime('%d %B %Y')}", [200, 1550, 1000, 1600], self.font_small, '#64748B', 20)
        self.draw_wrapped_text_in_rect(draw, "Цифриум - образование, которым делятся", [200, 1610, 1000, 1660], self.font_small, '#64748B', 20)
        
        png_path = os.path.join(self.output_dir, f"report_{student_id}.png")
        img.save(png_path)
        pdf_path = png_path.replace('.png', '.pdf')
        img.convert('RGB').save(pdf_path)
        
        return png_path, pdf_path
    
    def _generate_primary_report(self, student_data, period_name):
        img = Image.new('RGB', (1200, 1700), color='#0F172A')
        draw = ImageDraw.Draw(img)
        
        student_id = student_data.get('id', 'unknown')
        name = f"Ученик {student_id}"
        grade = student_data.get('grade', 4)
        total_tasks = student_data.get('total_tasks', 0)
        avg_score = student_data.get('avg_score', 0)
        homework_completion = student_data.get('homework_completion', 0)
        
        dino_location, location_name, xp = self.calculate_dino_location(total_tasks, avg_score, homework_completion)
        achievements = self.get_achievements(student_data)
        
        self.draw_wrapped_text_in_rect(draw, "ПУТЬ ДИНОЗАВРИКА ДИНО", [200, 40, 1000, 100], self.font_title, '#F1F5F9', 20)
        self.draw_wrapped_text_in_rect(draw, f"{name}, {grade} класс", [200, 110, 1000, 160], self.font_medium, '#94A3B8', 20)
        self.draw_wrapped_text_in_rect(draw, period_name, [200, 170, 1000, 210], self.font_small, '#64748B', 20)
        
        locations = ['Опушка', 'Тропинка', 'Поляна', 'Ручей', 'Болото', 'Пещера', 'Солнце']
        for i, loc in enumerate(locations):
            x = 150 + i * 130
            if i == dino_location:
                color = '#F97316'
                draw.ellipse([x-18, 280-18, x+18, 280+18], outline='#FFFFFF', width=2)
            else:
                color = '#64748B'
            draw.ellipse([x-15, 280-15, x+15, 280+15], fill=color)
            if i < 6:
                draw.line([x+15, 280, x+115, 280], fill='#64748B', width=3)
            draw.text((x, 320), loc, fill='#94A3B8', font=self.font_small, anchor='mt')
        
        draw.text((600, 370), f"Очки опыта (XP): {xp}", fill='#F97316', font=self.font_small, anchor='mt')
        
        for x in [200, 600, 1000]:
            draw.rectangle([x-150, 420, x+150, 580], fill='#1E293B', outline='#38BDF8', width=3)
        
        self.draw_text_in_rect(draw, str(total_tasks), [50, 420, 350, 500], self.font_large, '#38BDF8')
        self.draw_text_in_rect(draw, "решённых задач", [50, 510, 350, 580], self.font_small, '#94A3B8')
        
        self.draw_text_in_rect(draw, str(avg_score), [450, 420, 750, 500], self.font_large, '#38BDF8')
        self.draw_text_in_rect(draw, "средний балл (%)", [450, 500, 750, 580], self.font_small, '#94A3B8')
        
        self.draw_text_in_rect(draw, f"{homework_completion}%", [850, 420, 1150, 500], self.font_large, '#38BDF8')
        self.draw_text_in_rect(draw, "выполнение ДЗ", [850, 510, 1150, 580], self.font_small, '#94A3B8')
        
        draw.rectangle([200, 660, 1000, 820], fill='#FEF3C7', outline='#F97316', width=2)
        
        location_phrases = {
            0: "Дино стоит на опушке леса! Начни решать задачи, чтобы отправиться в путь!",
            1: "Дино учится обходить кочки! Каждая решённая задача приближает тебя к цели!",
            2: "Дино нашёл поляну знаний! Твой средний балл растёт — так держать!",
            3: "Дино переплывает ручей! Ты уже решил много задач и показал хорошие результаты!",
            4: "Дино в болоте! Не сдавайся — продолжай решать задачи, и мы выберемся!",
            5: "Дино у пещеры дракона! Ты почти у цели, осталось совсем немного!",
            6: "Дино достиг Солнца! Ты прошёл весь путь! Поздравляем!"
        }
        
        self.draw_wrapped_text_in_rect(draw, location_phrases.get(dino_location, "Дино ждёт тебя!"), [200, 660, 1000, 820], self.font_medium, '#92400E', 25)
        
        if achievements:
            self.draw_wrapped_text_in_rect(draw, "ТВОИ ДОСТИЖЕНИЯ", [200, 950, 1000, 1010], self.font_medium, '#F97316', 20)
            y_ach = 1030
            for ach in achievements:
                self.draw_wrapped_text_in_rect(draw, ach, [200, y_ach-20, 1000, y_ach+30], self.font_small, '#FFD700', 20)
                y_ach += 50
        
        self.draw_wrapped_text_in_rect(draw, f"{datetime.now().strftime('%d %B %Y')}", [200, 1550, 1000, 1600], self.font_small, '#64748B', 20)
        self.draw_wrapped_text_in_rect(draw, "Цифриум - учимся вместе с Дино", [200, 1610, 1000, 1660], self.font_small, '#64748B', 20)
        
        png_path = os.path.join(self.output_dir, f"report_{student_id}.png")
        img.save(png_path)
        pdf_path = png_path.replace('.png', '.pdf')
        img.convert('RGB').save(pdf_path)
        
        return png_path, pdf_path