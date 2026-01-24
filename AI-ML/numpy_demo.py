import numpy as np

# Create two NumPy arrays
a = np.array([10, 20, 30, 40])
b = np.array([1, 2, 3, 4])

print("Array A:", a)
print("Array B:", b)

# Element-wise operations
print("\nAddition:       ", a + b)
print("Subtraction:    ", a - b)
print("Multiplication: ", a * b)
print("Division:       ", a / b)

# Statistical operations
print("\nMean of A:", np.mean(a))
print("Median of A:", np.median(a))
print("Standard Deviation of A:", np.std(a))

# Dot product
print("\nDot Product of A and B:", np.dot(a, b))

# Matrix operations
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

print("\nMatrix A:\n", A)
print("Matrix B:\n", B)
print("Matrix Multiplication (A * B):\n", np.matmul(A, B))
