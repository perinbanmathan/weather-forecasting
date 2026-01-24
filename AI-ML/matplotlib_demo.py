import matplotlib.pyplot as plt

# Sample Data
x = [1, 2, 3, 4, 5]
y = [10, 20, 15, 25, 30]

# Create Line Plot
plt.plot(x, y, label='Sales Over Time', color='blue', marker='o', linestyle='-')

# Add Labels and Title
plt.xlabel('Days')
plt.ylabel('Sales')
plt.title('Line Plot Example - Daily Sales')

# Show Grid and Legend
plt.grid(True)
plt.legend()

# Display the plot
plt.show()
