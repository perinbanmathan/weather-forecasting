# Store input numbers
num1 = input('Enter first number: ')
num2 = input('Enter second number: ')

# Convert inputs to floats
a = float(num1)
b = float(num2)

# Perform operations
sum = a + b
difference = a - b
product = a * b
if b != 0:
    quotient = a / b
else:
    quotient = 'undefined (division by zero)'

# Display the results
print('The sum of {0} and {1} is {2}'.format(a, b, sum))
print('The difference of {0} and {1} is {2}'.format(a, b, difference))
print('The product of {0} and {1} is {2}'.format(a, b, product))
print('The quotient of {0} and {1} is {2}'.format(a, b, quotient))