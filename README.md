# YAP Platforms and Runtimes

Проект по дисциплине "Платформы и среды выполнения языков программирования".

- **ДЗ 1:** интерпретатор, который выполняет AST программы в формате JSON
- **ДЗ 2:** интерпретатор инструкций стековой машины
- **ДЗ 3:** компилятор JSON-AST (ДЗ 1) в инструкции стековой машины (ДЗ 2)

## Запуск ДЗ 1

```powershell
Get-Content -Raw program.json | python main.py
```

В `program.json` записан пример вычисления факториала. Входные числа берутся
из поля `input`. Результат примера - `120`.

## Запуск ДЗ 2

Интерпретатор принимает JSON из поля JSON representation сайта
Abstract Machine Compiler/Interpreter. Входные числа передаются через stdin.

Примеры запуска в PowerShell:

```powershell
"10" | python stack_machine.py machine_example.json
"5" | python stack_machine.py machine_factorial.json
```

Ожидаемые результаты: `7` и `120` соответственно.

## Запуск ДЗ 3

Компилятор читает AST в том же формате, что и ДЗ 1, и выдаёт JSON инструкций
стековой машины (формат ДЗ 2).

```powershell
# скомпилировать в файл и выполнить на стековой машине
python compiler.py program.json -o compiled_factorial.json
"5" | python stack_machine.py compiled_factorial.json

# вывести JSON в консоль / текстовый листинг / читать AST из stdin
python compiler.py program.json
python compiler.py program.json --asm
Get-Content -Raw program.json | python compiler.py
```

Ожидаемый результат для `program.json` (факториал 5) - `120`

## Основные файлы

- `main.py` - запуск первой домашки.
- `parser.py` - разбор JSON-AST.
- `ast_nodes.py` - выполнение узлов AST.
- `stack_machine.py` - выполнение инструкций стековой машины.
- `context.py`, `environment.py` - ввод, вывод и переменные.
- `program.json` - пример программы для ДЗ 1.
- `machine_factorial.json` - пример программы для ДЗ 2.
- `machine_example.json` - JSON инструкций со второго сайта.
- `compiler.py` - компилятор JSON-AST в инструкции стековой машины.
- `compiled_factorial.json` - результат компиляции `program.json`.

Машина поддерживает `READ`, `WRITE`, `LD`, `ST`, `CONST`, `BINOP`, `LABEL`,
`JMP`, `JZ`, `JNZ`. JSON содержит массив: `"READ"`, `"WRITE"` и объекты
вроде `{"CONST": 3}` или `{"LD": "x"}`. Арифметика и логические операции работают так же, как в первой домашке.

## Тесты

```powershell
python tests.py
python -m unittest -v test_stack_machine
python -m unittest -v test_compiler
```

## Авторы

Grankina Elizabeth

Sadygov Huseyn

Yaroslav Grigoriev

Berezhnoy Yan
