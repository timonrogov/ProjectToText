# scripts/check_resources.py
"""Проверяет наличие всех необходимых файлов перед сборкой."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

REQUIRED = [
    "main.py",
    "requirements.txt",
    "resources/default_profile.json",
    "resources/styles/main.qss",
    "core/__init__.py",
    "core/models.py",
    "core/scanner.py",
    "core/filter_engine.py",
    "core/generator.py",
    "core/analytics.py",
    "core/profile_manager.py",
    "core/utils.py",
    "gui/__init__.py",
    "gui/main_window.py",
    "gui/file_tree_panel.py",
    "gui/file_tree_model.py",
    "gui/settings_panel.py",
    "gui/output_panel.py",
    "gui/action_buttons.py",
    "gui/status_bar_widget.py",
    "gui/skipped_files_dialog.py",
    "gui/menu_bar.py",
    "workers/__init__.py",
    "workers/scan_worker.py",
    "workers/generate_worker.py",
]

print("Проверка файлов проекта...")
all_ok = True
for rel in REQUIRED:
    path = ROOT / rel
    status = "✅" if path.exists() else "❌ ОТСУТСТВУЕТ"
    if not path.exists():
        all_ok = False
    print(f"  {status}  {rel}")

# Иконки (предупреждение, не ошибка)
icons = {
    "Windows": ROOT / "resources/icons/app_icon.ico",
    "macOS":   ROOT / "resources/icons/app_icon.icns",
    "Linux":   ROOT / "resources/icons/app_icon.png",
}
print("\nПроверка иконок:")
for platform, path in icons.items():
    status = "✅" if path.exists() else "⚠️  отсутствует (сборка продолжится без иконки)"
    print(f"  {status}  {platform}: {path.name}")

print()
if all_ok:
    print("✅ Все файлы на месте. Можно запускать сборку.")
    sys.exit(0)
else:
    print("❌ Некоторые файлы отсутствуют. Исправьте ошибки перед сборкой.")
    sys.exit(1)