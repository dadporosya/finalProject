from pyexpat.errors import messages
class Converter:
    def moveOnce(self, d):
        if d=='u':
            return 72
        elif d=='l':
            return 73
        elif d=='d':
            return 74
        elif d=="r":
            return 75
        else:
            return ''

    def move(self, s):
        print(h(len(s)))
        result=''
        for m in s:
            result+=str(self.moveOnce(m))+'\n'
        return result

def hexStr(text:str):
    text=str(text)
    hex_value = text.encode().hex()
    return hex_value

def hexInt(i:int):
    s = str(format(i, "x"))
    if len(s) == 1:
        s = '0'+s
    return s

def h(arg):
    if type(arg) == int:
        return hexInt(arg)
    elif type(arg) == str:
        return hexStr(arg)
    elif type(arg) == list:
        for a in list(arg):
            print(h(a))

c = Converter()

start = "RVR0"

print(h(start))
print(c.move("uurrddrrddddddlllluurruulllllluurru"))


# messages = [start, '1', '1 1 16']
#
# for m in messages:
#     print(hex(m))
#
# cmds = []
#
# message = 'Blackbox Cup'
# header = "01 "
# counter = 0
# for m in message:
#     cmds.append(header + hexInt(counter) + ' ' + hexStr(m))
#     counter+=1
#
# message = 'Blackbox Cup'
# header = "40 "
# counter = 0
# for m in message:
#     cmds.append(header + hexInt(counter))
#     counter+=1
#
# print(hexStr(start))
# print(hexInt(len(cmds)))
# for cmd in cmds:
#     print(cmd)