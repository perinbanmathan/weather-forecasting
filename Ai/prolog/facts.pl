father(john, mary).
father(john, tom).

mother(susan, mary).
mother(susan, tom).

parent(X, Y) :- father(X, Y).
parent(X, Y) :- mother(X, Y).
