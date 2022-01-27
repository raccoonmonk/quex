# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from math import log

def get(Word, WordList):
    L = len(Word)
    if L == 0: return -1

    required_n   = log(float(len(Word)), 3)
    min_distance = None
    min_i        = -1

    for i in range(len(WordList)):
        distance = compute_distance(Word, WordList[i])
        if min_distance is None or distance < min_distance: 
            min_i        = i
            min_distance = distance
    
    if min_distance < required_n: return min_i
    else:                         return -1

def compute_distance(A, B):
    vector = compute_motion_vector(A, B)
    prev_move = -1000
    sum = 0.0
    for i in range(len(A)):
        move = vector[i]
        if i == len(B):                        sum += (len(A) - len(B)) + prev_move; break
        if   B[i] == A[i]:                     prev_move = 0; continue
        elif B[i].lower() == A[i].lower():     sum += 0.1; continue
        elif is_quite_close(B[i], A[i]):       sum += 0.2; continue
        elif move != 0 and move == prev_move:  pass
        else:                                  sum += 1.0
        prev_move = move

    delta_L = abs(len(B) - len(A))
    sum += delta_L * 2.0 / 3.0
    return sum

def is_quite_close(A, B):
    aux = [A.lower(), B.lower()]
    aux.sort()
    x = aux[0]; y = aux[1]
    tolerated = [ ["s", "z"], ["f", "w"], ["m", "n"], ["o", "u"], ["c", "k"], ["c", "z"], ["d", "t"], ["b", "p"], ["i", "u"], ["e", "i"] ]
    for a, b in tolerated:
        if x == a and y == b: return True
    return False

def get_motion(Letter, Word, i):
    """Only consider 'motions' of one character. If a letter
       only needs to be move by one position, this is 1/2 an error."""
    LWord = len(Word)
    if i >= LWord - 1:    return 0

    if Word[i].lower() == Letter.lower(): return 0

    if i > 0: 
        if Word[i - 1].lower() == Letter.lower(): return  -1
    if i < LWord:
        if Word[i + 1].lower() == Letter.lower(): return 1
    return 0

def compute_motion_vector(A, B):
    vector = []
    i = -1
    for letter in A:
        i += 1
        vector.append(get_motion(letter, B, i))

    return vector


if __name__ == "__main__":
    word_list = [ "eins", "schifffahrt", "drei", "sieben" ]

    for word in ["ains", "zwei", "trei", "sibeen", "vier", "acht", "schiffahrt"]:
        print("%s:" % word)
        for candidate in word_list:
            print("    %s: %s" % (candidate, compute_motion_vector(word, candidate)))



