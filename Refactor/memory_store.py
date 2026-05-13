memory=[]

def save_context(q,a):

    memory.append({
    "question":q,
    "answer":a
    })

def get_context():

    return memory[-3:]