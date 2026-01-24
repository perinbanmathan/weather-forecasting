import seaborn as sns
import matplotlib_demo.pyplot as plt

# Load a built-in dataset (Titanic)
df = sns.load_dataset("titanic")

# Display first 5 rows
print(df.head())

# Set plot style
sns.set(style="darkgrid")

# 1. Count Plot: Number of survivors by gender
sns.countplot(x='sex', hue='survived', data=df)
plt.title('Survival Count by Gender')
plt.show()

# 2. Bar Plot: Average fare by class
sns.barplot(x='class', y='fare', data=df)
plt.title('Average Fare by Class')
plt.show()

# 3. Box Plot: Age distribution by class
sns.boxplot(x='class', y='age', data=df)
plt.title('Age Distribution by Class')
plt.show()

# 4. Heatmap: Correlation between numerical features
corr = df.corr(numeric_only=True)
sns.heatmap(corr, annot=True, cmap='coolwarm')
plt.title('Correlation Heatmap')
plt.show()

# 5. Pair Plot: Relationships between features
sns.pairplot(df[['age', 'fare', 'survived']], hue='survived')
plt.suptitle('Pair Plot of Age, Fare, and Survival', y=1.02)
plt.show()
