# Cycle08 source cases

Local synthetic truth audit; no provider responses or empirical launch.

## t_9ea3e5ba9a652c481433

Operators: + / +.

### N = 4

~~~python
a = 411
b = 828
c = 633
for i in range(4):
    a = (a * b + c) % 997
    b = (b * c + a) % 997
    if b < c:
        c = (c + b) % 997
    c = (c * a + b) % 997
a = (a + b) % 997
b = (b + c) % 997
result = (a % 3 == 1)
~~~

Verified answer: false.
Executed statements: 29.

### N = 64

~~~python
a = 411
b = 828
c = 633
for i in range(64):
    a = (a * b + c) % 997
    b = (b * c + a) % 997
    if b < c:
        c = (c + b) % 997
    c = (c * a + b) % 997
a = (a + b) % 997
b = (b + c) % 997
result = (a % 3 == 1)
~~~

Verified answer: true.
Executed statements: 361.

## t_ce6df55b96bb7ce9649e

Operators: + / -.

### N = 4

~~~python
a = 130
b = 135
c = 308
for i in range(4):
    a = (a * b + c) % 997
    b = (b * c - a) % 997
    if b < c:
        c = (c + b) % 997
    c = (c * a + b) % 997
a = (a + b) % 997
b = (b + c) % 997
result = (a % 3 == 0)
~~~

Verified answer: false.
Executed statements: 28.

### N = 64

~~~python
a = 130
b = 135
c = 308
for i in range(64):
    a = (a * b + c) % 997
    b = (b * c - a) % 997
    if b < c:
        c = (c + b) % 997
    c = (c * a + b) % 997
a = (a + b) % 997
b = (b + c) % 997
result = (a % 3 == 0)
~~~

Verified answer: false.
Executed statements: 355.

## t_dd29af39a9e52039b5b9

Operators: - / +.

### N = 4

~~~python
a = 48
b = 704
c = 725
for i in range(4):
    a = (a * b - c) % 997
    b = (b * c + a) % 997
    if b < c:
        c = (c + b) % 997
    c = (c * a + b) % 997
a = (a + b) % 997
b = (b + c) % 997
result = (a % 3 == 1)
~~~

Verified answer: false.
Executed statements: 29.

### N = 64

~~~python
a = 48
b = 704
c = 725
for i in range(64):
    a = (a * b - c) % 997
    b = (b * c + a) % 997
    if b < c:
        c = (c + b) % 997
    c = (c * a + b) % 997
a = (a + b) % 997
b = (b + c) % 997
result = (a % 3 == 1)
~~~

Verified answer: false.
Executed statements: 364.

## t_7c960451884d27194472

Operators: - / -.

### N = 4

~~~python
a = 301
b = 872
c = 367
for i in range(4):
    a = (a * b - c) % 997
    b = (b * c - a) % 997
    if b < c:
        c = (c + b) % 997
    c = (c * a + b) % 997
a = (a + b) % 997
b = (b + c) % 997
result = (a % 3 == 2)
~~~

Verified answer: false.
Executed statements: 28.

### N = 64

~~~python
a = 301
b = 872
c = 367
for i in range(64):
    a = (a * b - c) % 997
    b = (b * c - a) % 997
    if b < c:
        c = (c + b) % 997
    c = (c * a + b) % 997
a = (a + b) % 997
b = (b + c) % 997
result = (a % 3 == 2)
~~~

Verified answer: true.
Executed statements: 361.

Decision: consider_execution_freeze.
Any empirical experiment requires its own execution freeze.
