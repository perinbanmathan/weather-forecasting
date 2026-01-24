from pyswip import Prolog

# Step 1: Create Prolog engine
prolog = Prolog()

# Step 2: Define Knowledge Base (facts)
prolog.assertz("father(john, mary)")
prolog.assertz("father(john, tom)")
prolog.assertz("mother(susan, mary)")
prolog.assertz("mother(susan, tom)")

# Step 3: Define Rules (inference engine)

prolog.assertz("parent(X, Y) :- father(X, Y)")
prolog.assertz("parent(X, Y) :- mother(X, Y)")
prolog.assertz("sibling(X, Y) :- parent(Z, X), parent(Z, Y), X \\= Y")
prolog.assertz("grandparent(X, Y) :- parent(X, Z), parent(Z, Y)")

# Step 4: Queries from Python
print("Children of John:")
for result in prolog.query("father(john, X)"):
    print(f" - {result['X']}")

print("\nSiblings of Mary:")
for result in prolog.query("sibling(mary, X)"):
    print(f" - {result['X']}")

print("\nGrandparent relationships:")
for result in prolog.query("grandparent(X, Y)"):
    print(f" - {result['X']} is grandparent of {result['Y']}")