# Cycle07 development cases

These are the eight already-used development items in collection order.
Only development programs are shown here. Both solver responses and truth are
public result metadata; truth was never included in the submitted payload.

## i_57e9139fc06e45a0e265

Stratum: sequential; first role: G; executed statements: 11.
Truth: false; G: false; S: false.

```python
a = 7
b = 7
c = 1
a = a + b
b = (a + c) % 5
if b == c:
    a = a + c
c = c + b
if a % 2 == 0:
    b = b + a
a = (a + b) + c
result = (a % 3 == 0)
```

## i_7953719d160d6936a210

Stratum: bounded_loop; first role: G; executed statements: 32.
Truth: true; G: true; S: true.

```python
a = 4
b = 3
c = 6
for i in range(5):
    a = a + b
    b = (b + i) % 6
    if b == c:
        a = a - i
    c = (c + a) % 12
b = b + c
a = (a - b) + c
result = (a % 3 == 1)
```

## i_9b36d387966e0fcb36d0

Stratum: sequential; first role: G; executed statements: 10.
Truth: true; G: true; S: true.

```python
a = 1
b = 4
c = 3
a = a + b
b = (a + c) % 6
if b > c:
    a = a * c
c = c + b
if a % 2 == 0:
    b = b + a
a = (a + b) + c
result = (a % 3 == 0)
```

## i_c4d0eee2348c3c41c4eb

Stratum: bounded_loop; first role: S; executed statements: 33.
Truth: false; G: false; S: false.

```python
a = 1
b = 6
c = 6
for i in range(5):
    a = a + b
    b = (b + i) % 5
    if b > c:
        a = a + i
    c = (c + a) % 9
b = b + c
a = (a + b) + c
result = (a % 3 == 2)
```

## i_4a531510378b329b11e3

Stratum: bounded_loop; first role: G; executed statements: 37.
Truth: false; G: false; S: false.

```python
a = 2
b = 4
c = 2
for i in range(6):
    a = a + b
    b = (b + i) % 8
    if b == c:
        a = a + i
    c = (c + a) % 10
b = b + c
a = (a - b) + c
result = (a % 3 == 1)
```

## i_8b79c068abf5e4116764

Stratum: sequential; first role: S; executed statements: 12.
Truth: false; G: false; S: false.

```python
a = 7
b = 3
c = 6
a = a + b
b = (a + c) % 7
if b < c:
    a = a + c
c = c + b
if a % 2 == 0:
    b = b + a
a = (a + b) + c
result = (a % 3 == 2)
```

## i_288bd482923785d704ae

Stratum: sequential; first role: S; executed statements: 11.
Truth: true; G: true; S: true.

```python
a = 6
b = 4
c = 2
a = a + b
b = (a + c) % 8
if b == c:
    a = a - c
c = c + b
if a % 2 == 0:
    b = b + a
a = (a - b) + c
result = (a % 3 == 2)
```

## i_31c2ddf4fe97394512ea

Stratum: bounded_loop; first role: S; executed statements: 23.
Truth: true; G: true; S: true.

```python
a = 5
b = 5
c = 5
for i in range(3):
    a = a + b
    b = (b + i) % 5
    if b == c:
        a = a + i
    c = (c + a) % 11
b = b + c
a = (a + b) - c
result = (a % 3 == 1)
```
