import subprocess
import sys

def run_script(script_name):
    try:
        subprocess.run([sys.executable, script_name], check=True)
    except subprocess.CalledProcessError:
        print(f"\n❌ Произошла ошибка при запуске {script_name}.\n")

def main_menu():
    while True:
        print("\n========== МЕНЮ ПРОЕКТА ==========")
        print("1. Запустить парсер (parser.py)")
        print("2. Запустить анализ (analysis.py)")
        print("3. Запустить ВСЁ (сбор + анализ)")
        print("0. Выход")
        print("==================================")
        
        choice = input("Выберите действие: ").strip()
        
        if choice == "1":
            run_script("parser.py")
        elif choice == "2":
            run_script("analysis.py")
        elif choice == "3":
            run_script("parser.py")
            run_script("analysis.py")
        elif choice == "0":
            print("Выход из программы.")
            break
        else:
            print("Неверный ввод. Пожалуйста, выбери 0-3.")

if __name__ == "__main__":
    main_menu()
