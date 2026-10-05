# YAP Platforms and Runtimes

Проект по дисциплине «Платформы и среды выполнения языков программирования».

## Домашняя работа 1

Интерпретатор принимает AST в JSON-представлении из стандартного ввода:

```powershell
Get-Content -Raw program.json | python main.py
```

## Домашняя работа 2

Компилятор переводит JSON AST в программу стековой абстрактной машины. Машинный код можно сохранить в текстовом формате или JSON, запустить отдельно либо выполнить AST сразу после компиляции:

```powershell
python stack_machine.py compile program.json -o program.sm
python stack_machine.py compile program.json --format json -o program.machine.json
python stack_machine.py run program.sm --input input.txt
python stack_machine.py exec program.json
```

При `exec` входные данные берутся из поля `input` в AST. Параметр `--input` задаёт файл с разделёнными пробелами токенами и переопределяет это поле.

Инструкции `CONST`, `LD` и `READ` кладут значение в стек. `BINOP` снимает правый, затем левый операнд и кладёт результат; `ST`, `WRITE`, `JZ` и `JNZ` снимают верхнее значение. `JZ` переходит по метке при нуле, `JNZ` — при ненулевом значении.

## Авторы

- Grankina Elizabeth
- Sadygov Huseyn
- Yaroslav Grigoriev
