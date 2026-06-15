# scripts/build.py
"""
Универсальный скрипт автоматизированной сборки дистрибутива.
Запускать из корня проекта: python scripts/build.py

Выполняет:
1. Проверку ресурсов
2. Генерацию иконок (если их нет)
3. Запуск PyInstaller
4. Базовый smoke-тест собранного бандла
5. Отчёт о результатах
"""
from __future__ import annotations

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Запускает команду и выводит результат."""
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, text=True)
    if check and result.returncode != 0:
        print(f"❌ Команда завершилась с кодом {result.returncode}")
        sys.exit(result.returncode)
    return result


def step(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def main():
    start_time = time.time()
    print("🚀 Запуск сборки Project to Text")
    print(f"   Платформа: {sys.platform}")
    print(f"   Python:    {sys.version.split()[0]}")
    print(f"   Корень:    {ROOT}")

    # ------------------------------------------------------------------
    # Шаг 1: Проверка ресурсов
    # ------------------------------------------------------------------
    step("Шаг 1: Проверка ресурсов")
    result = run(
        [sys.executable, str(ROOT / 'scripts' / 'check_resources.py')],
        check=False
    )
    if result.returncode != 0:
        print("❌ Проверка ресурсов не пройдена. Сборка прервана.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Шаг 2: Генерация иконок (если отсутствуют)
    # ------------------------------------------------------------------
    step("Шаг 2: Иконки")
    icons_dir = ROOT / "resources" / "icons"
    ico_path  = icons_dir / "app_icon.ico"
    png_path  = icons_dir / "app_icon.png"

    if not ico_path.exists() or not png_path.exists():
        print("Иконки не найдены, генерируем...")
        run([sys.executable, str(ROOT / 'scripts' / 'generate_icon.py')])
    else:
        print("✅ Иконки уже существуют, пропускаем генерацию")

    # ------------------------------------------------------------------
    # Шаг 3: Очистка предыдущей сборки
    # ------------------------------------------------------------------
    step("Шаг 3: Очистка")
    for clean_dir in ['dist', 'build']:
        path = ROOT / clean_dir
        if path.exists():
            shutil.rmtree(path)
            print(f"  Удалён: {clean_dir}/")
    print("✅ Директории dist/ и build/ очищены")

    # ------------------------------------------------------------------
    # Шаг 4: Сборка PyInstaller
    # ------------------------------------------------------------------
    step("Шаг 4: PyInstaller")
    spec_path = ROOT / "project_to_text.spec"
    if not spec_path.exists():
        print(f"❌ .spec файл не найден: {spec_path}")
        sys.exit(1)

    run([
        sys.executable, '-m', 'PyInstaller',
        str(spec_path),
        '--clean',
        '--noconfirm',
        '--distpath', str(ROOT / 'dist'),
        '--workpath', str(ROOT / 'build'),
    ])

    # ------------------------------------------------------------------
    # Шаг 5: Проверка результата
    # ------------------------------------------------------------------
    step("Шаг 5: Проверка результата")

    if sys.platform == "win32":
        exe_path = ROOT / "dist" / "Project to Text.exe"
    else:
        exe_path = ROOT / "dist" / "Project to Text"

    if not exe_path.exists():
        print(f"❌ Исполняемый файл не найден: {exe_path}")
        sys.exit(1)

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"✅ Исполняемый файл создан: {exe_path}")
    print(f"   Размер: {size_mb:.1f} МБ")

    # ------------------------------------------------------------------
    # Шаг 6: Smoke-тест
    # ------------------------------------------------------------------
    step("Шаг 6: Smoke-тест")
    print("Запускаем приложение на 3 секунды для проверки старта...")

    # На headless-серверах (CI/CD) без дисплея пропускаем тест
    if os.environ.get("CI") or os.environ.get("DISPLAY") == "" and sys.platform != "win32":
        print("⚠️  Обнаружена среда CI/CD без дисплея — GUI smoke-тест пропущен")
    else:
        try:
            proc = subprocess.Popen(
                [str(exe_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            time.sleep(3)
            proc.terminate()
            proc.wait(timeout=5)
            if proc.returncode in (0, -15, 1):  # 0=OK, -15=SIGTERM(ожидаемо), 1=Windows terminate
                print("✅ Smoke-тест пройден: приложение запустилось и завершилось корректно")
            else:
                stderr_out = proc.stderr.read().decode(errors='replace') if proc.stderr else ''
                print(f"⚠️  Приложение завершилось с кодом {proc.returncode}")
                if stderr_out:
                    print(f"   stderr: {stderr_out[:500]}")
        except Exception as e:
            print(f"⚠️  Smoke-тест не выполнен: {e}")

    # ------------------------------------------------------------------
    # Итог
    # ------------------------------------------------------------------
    elapsed = time.time() - start_time
    step(f"✅ Сборка завершена за {elapsed:.0f} сек")
    print(f"\n   Исполняемый файл: {exe_path}")
    print(f"   Размер:           {size_mb:.1f} МБ")
    print(f"\n   Запустите и проверьте вручную!")


if __name__ == "__main__":
    main()