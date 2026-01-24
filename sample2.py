n=2

flag=False

if n==1 or n==0:
    flag==False
elif n>1:
    for i in range(2,n):
        if(n%i)==0:
         flag = True
        break
if flag:
    print(n," is prime number")
else:
    print(n," is not prime number")


