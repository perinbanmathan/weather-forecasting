import pandas as pd

# 1. Create a sample DataFrame (like a table)
data = {
    'Name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
    'Age': [25, 30, 35, 40, 28],
    'City': ['Chennai', 'Mumbai', 'Delhi', 'Chennai', 'Delhi'],
    'Salary': [50000, 60000, 70000, 80000, 52000]
}

df = pd.DataFrame(data)

print("Original DataFrame:\n", df)

# 2. Filter: Employees older than 30
older_than_30 = df[df['Age'] > 30]
print("\nEmployees older than 30:\n", older_than_30)

# 3. Add a new column: Bonus (10% of salary)
df['Bonus'] = df['Salary'] * 0.10
print("\nDataFrame with Bonus column:\n", df)

# 4. Modify: Increase all salaries by ₹2000
df['Salary'] = df['Salary'] + 2000
print("\nUpdated Salary:\n", df)

# 5. Sort: By salary (descending)
sorted_df = df.sort_values(by='Salary', ascending=False)
print("\nSorted by Salary (High to Low):\n", sorted_df)

# 6. Group: Average salary by City
grouped_salary = df.groupby('City')['Salary'].mean()
print("\nAverage Salary by City:\n", grouped_salary)

# 7. Save to CSV
df.to_csv("employees.csv", index=False)
print("\nData saved to employees.csv")
