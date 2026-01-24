n=int(input("enter the size of list: "))
a=[]
for i in range(n):
    num=int(input("ente the list elements: "))
    a.append(num)
print(a)
max=a[0]
for i in range(n):
    if(max<a[i]):
        max=a[i]
print("maximum",max)