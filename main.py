import copy
from Types import *
from Functions import *
import pymorphy2
from Attempts_module import Attempts

morph = pymorphy2.MorphAnalyzer()
import networkx as nx
import matplotlib.pyplot as plt
from networkx.drawing.nx_agraph import write_dot, graphviz_layout
import psycopg2
import math
import sys

class GPattern:
    def __init__(self, l=-1, textWord="", nw="", p="", m=0.0):
        self.level = l
        self.dependentWord = textWord
        self.dependentWordConstraints = []  # массив лямбда-функций ограничений на морф
        self.normalWord = nw
        self.mark = m
        self.info = ""  # ????

    def __repr__(self):
        s = str(self.level) + ":"
        if self.level == 3:
            s += " " + self.normalWord
        for c in self.dependentWordConstraints:
            s += " " + c[1][1] + ";"
        return s

    def __lt__(self, other): # x < y
        if self.level < other.level:
            return True
        if self.level > other.level:
            return False
        return self.mark < other.mark

def extractFirstLevel(word, curMorph, con):
    s0 = "SELECT id FROM morph_constraints WHERE " + \
         "s_cl = %s AND " + \
         "(animate = %s OR animate = \'not_imp\') AND " + \
         "(gender = %s OR gender = \'not_imp\')  AND " + \
         "(number = %s OR number = \'not_imp\') AND " + \
         "(case_morph = %s OR case_morph = \'not_imp\') AND " + \
         "(reflection = %s OR reflection = \'not_imp\') AND " + \
         "(perfective = %s OR perfective = \'not_imp\') AND " + \
         "(transitive = %s OR transitive = \'not_imp\') AND " + \
         "(person = %s OR person = \'not_imp\') AND " + \
         "(tense = %s OR tense = \'not_imp\') AND " + \
         "(voice = %s OR voice = \'not_imp\') AND " + \
         "(degree = %s OR degree = \'not_imp\') AND " + \
         "(static = %s OR static = \'not_imp\')"

    # получение морфа
    # s1 - получение номера главного слова(одно слово в идеале)
    s2 = "SELECT * FROM gpattern_1_level WHERE main_morph IN (" + s0 + ")"
    s3 = "SELECT  mark, morph_constraints.* FROM (" + s2 + ") AS t JOIN morph_constraints ON morph_constraints.id = dep_morph ORDER BY mark DESC;"
    cursor = con.cursor()
    params = (curMorph.s_cl, curMorph.animate, curMorph.gender, curMorph.number, \
              curMorph.case_morph, curMorph.reflection, curMorph.perfective, curMorph.transitive, \
              curMorph.person, curMorph.tense, curMorph.voice, curMorph.degree, curMorph.static)
    cursor.execute(s3, params)
    ans = cursor.fetchall()
    firLev = []
    for cur in ans:
        curPatt = GPattern(1)
        curConstr = []
        # print("--------------")
        for j in range(2, 15):  # 13 - количество свойств в Morph
            if cur[j] != 'not_imp':
                curProp = Morph.names[j - 2]
                curConstr.append(((lambda m, cP, val: getattr(m, cP) == val), (curProp, cur[j])))
                # print(curProp, cur[j])
        curPatt.dependentWordConstraints = curConstr
        curPatt.mark = cur[0]
        if len(curConstr) > 0:
            firLev.append(curPatt)
    cursor.close()
    return firLev


def extractSecondLevel(word, curMorph, con):
    s0 = "SELECT id FROM morph_constraints WHERE " + \
         "s_cl = %s AND " + \
         "(animate = %s OR animate = \'not_imp\') AND " + \
         "(gender = %s OR gender = \'not_imp\')  AND " + \
         "(number = %s OR number = \'not_imp\') AND " + \
         "(case_morph = %s OR case_morph = \'not_imp\') AND " + \
         "(reflection = %s OR reflection = \'not_imp\') AND " + \
         "(perfective = %s OR perfective = \'not_imp\') AND " + \
         "(transitive = %s OR transitive = \'not_imp\') AND " + \
         "(person = %s OR person = \'not_imp\') AND " + \
         "(tense = %s OR tense = \'not_imp\') AND " + \
         "(voice = %s OR voice = \'not_imp\') AND " + \
         "(degree = %s OR degree = \'not_imp\') AND " + \
         "(static = %s OR static = \'not_imp\')"

    # получение морфа
    # s1 - получение номера главного слова(одно слово в идеале)
    s2 = "SELECT * FROM gpattern_2_level WHERE main_morph IN (" + s0 + ") AND gpattern_2_level.main_word = " + \
         "(SELECT id FROM word WHERE name = %s)"
    s3 = "SELECT  mark, morph_constraints.* FROM (" + s2 + ") AS t JOIN morph_constraints ON morph_constraints.id = dep_morph ORDER BY mark DESC;"
    cursor = con.cursor()
    params = (curMorph.s_cl, curMorph.animate, curMorph.gender, curMorph.number, \
              curMorph.case_morph, curMorph.reflection, curMorph.perfective, curMorph.transitive, \
              curMorph.person, curMorph.tense, curMorph.voice, curMorph.degree, curMorph.static, word)
    cursor.execute(s3, params)
    ans = cursor.fetchall()
    secLev = []
    for cur in ans:
        curPatt = GPattern(2)
        curConstr = []
        # print("-------------")
        for j in range(2, 15):  # 13 - количество свойств в Morph
            if cur[j] != 'not_imp':
                curProp = Morph.names[j - 2]
                curConstr.append(((lambda m, cP, val: getattr(m, cP) == val), (curProp, cur[j])))
                # print(curProp, cur[j])

        curPatt.dependentWordConstraints = curConstr
        curPatt.mark = cur[0]
        if len(curConstr) > 0:
            secLev.append(curPatt)
    cursor.close()
    return secLev


def extractThirdLevel(word, curMorph, con):
    s0 = "SELECT id FROM morph_constraints WHERE " + \
         "s_cl = %s AND " + \
         "(animate = %s OR animate = \'not_imp\') AND " + \
         "(gender = %s OR gender = \'not_imp\')  AND " + \
         "(number = %s OR number = \'not_imp\') AND " + \
         "(case_morph = %s OR case_morph = \'not_imp\') AND " + \
         "(reflection = %s OR reflection = \'not_imp\') AND " + \
         "(perfective = %s OR perfective = \'not_imp\') AND " + \
         "(transitive = %s OR transitive = \'not_imp\') AND " + \
         "(person = %s OR person = \'not_imp\') AND " + \
         "(tense = %s OR tense = \'not_imp\') AND " + \
         "(voice = %s OR voice = \'not_imp\') AND " + \
         "(degree = %s OR degree = \'not_imp\') AND " + \
         "(static = %s OR static = \'not_imp\')"

    # получение морфа
    # s1 - получение номера главного слова(одно слово в идеале)
    s2 = "SELECT * FROM gpattern_3_level WHERE main_morph IN (" + s0 + ") AND gpattern_3_level.main_word = " + \
         "(SELECT id FROM word WHERE name = %s)"
    s3 = "SELECT  mark, morph_constraints.*, word.name FROM (" + s2 + ") AS t JOIN morph_constraints ON morph_constraints.id = dep_morph " + \
         "JOIN word ON dep_word = word.id ORDER BY mark DESC;"
    cursor = con.cursor()
    params = (curMorph.s_cl, curMorph.animate, curMorph.gender, curMorph.number, \
              curMorph.case_morph, curMorph.reflection, curMorph.perfective, curMorph.transitive, \
              curMorph.person, curMorph.tense, curMorph.voice, curMorph.degree, curMorph.static, word)
    cursor.execute(s3, params)
    ans = cursor.fetchall()
    thirdLev = []
    for cur in ans:
        curPatt = GPattern(3)
        curConstr = []
        # print("-----------------")
        for j in range(2, 15):  # 13 - количество свойств в Morph
            if cur[j] != 'not_imp':
                curProp = Morph.names[j - 2]
                curConstr.append(((lambda m, cP, val: getattr(m, cP) == val), (curProp, cur[j])))
                # print(curProp, cur[j])
        curPatt.normalWord = cur[15]
        curPatt.dependentWordConstraints = curConstr
        curPatt.mark = cur[0]
        if len(curConstr) > 0:
            thirdLev.append(curPatt)
    cursor.close()
    return thirdLev


class Word:
    def morphParse(self):
        p = morph.parse(self.word)
        numberWord = self.numberInSentence
        numberVariant = 0
        curListNumbersVariants = []
        for curParse in p:
            m = parseToMorph(self.word, curParse)
            self.morph.append(m)
            self.normalWord.append(curParse.normal_form)
            curListNumbersVariants.append((numberWord, numberVariant))
            numberVariant += 1
        return curListNumbersVariants

    def getGPatterns(self, con):
        for i in range(len(self.morph)):
            curMorph = self.morph[i]
            curNormal = self.normalWord[i]
            curPatterns = []
            curFirst = extractFirstLevel(curNormal, curMorph, con)
            curSec = extractSecondLevel(curNormal, curMorph, con)
            curThird = extractThirdLevel(curNormal, curMorph, con)
            curPatterns += curThird
            curPatterns += curSec
            curPatterns += curFirst
            self.gPatterns.append(curPatterns)
        return self.gPatterns

    def __init__(self, name="", number=-1):
        self.word = name  # у Одинцева Word
        self.normalWord = []  # список начальных форм слов, соответствует morph(вместе заполняются)
        self.morph = []  # список объектов типа Morph

        # список морфологических характеристик для всех вариантов морф. анализа
        self.gPatterns = []  # список из списоков из Gpattern, i элемент - для i morph
        # с помощью морф.анализатора заполняем morph, с помощью базы - GPatterns
        self.numberInSentence = number


class Gp:
    def __init__(self, mod, dw):
        self.model = mod
        self.depWord = dw


class ParsePointWord:
    def __init__(self):
        self.word = Word()
        self.parsed = False
        self.usedMorphAnswer = Morph()
        self.usedGp = []  # типа Gp


class ParsePoint:
    directForIsApplicable = 1

    def __init__(self, ppwl, cl, mark, cpw, par, num, att, g):
        self.parsePointWordList = ppwl
        self.childParsePoint = cl
        self.markParsePoint = mark
        self.countParsedWords = cpw
        self.parsed = par
        self.numberPoint = num
        self.attempts = att
        self.graph = g# хранится граф (networkx)

    def __repr__(self):
        ans = str(self.numberPoint) + ":"
        for i in self.parsed:
            ans += str(i[0]) + "+" + str(i[1]) + ";"
        return ans

    def getMark(self, parentMark):
        '''return mark of ParsePoint and count of parsed word in this ParsePoint'''
        summ = 0
        countParsedWord = 0
        for curPointWord in self.parsePointWordList:
            if (curPointWord.parsed):
                countParsedWord += 1
                for curGp in curPointWord.usedGp:
                    summ += math.log(curGp.model.mark)
        return ((summ + parentMark), countParsedWord)

    def index(self,
              word1):  # ищет в списке слов в данной точке разбора индекс данного слова(класса Word), вспомогательная функция
        for i in range(len(self.parsePointWordList)):
            if self.parsePointWordList[i].word == word1:
                return i
        return None

    def checkInderectDependency(self, numberMain, numberDep):
        depWord = self.parsePointWordList[numberDep]
        mainWord = self.parsePointWordList[numberMain]
        return True  # ПЕРЕПИСАТЬ!!!!

    def checkIsWordInDependentGroup(self, numberMain, numberDep):
        return True  # ПЕРЕПИСАТЬ!!!!!

    def checkMorph(self, morph, constraints):
        for cur in constraints:
            curCheckFun = cur[0]
            curProperty = cur[1][0]
            val = cur[1][1]
            if not curCheckFun(morph, curProperty, val):
                return False
        return True

    def checkWord(self, depWord, parseVariant,
                  gPattern):  # на вход - потенциальное зависимое слово(или потенциальный предлог), модель управления
        #  Удовлетворяет ли требованиям данный вариант разбора данного слова
        constr = gPattern.dependentWordConstraints
        morphForm = depWord.morph[parseVariant]
        normal = depWord.normalWord[parseVariant]
        if gPattern.level != 3 or (gPattern.level == 3 and gPattern.normalWord == normal):
            if (self.checkMorph(morphForm, constr)):
                return True
        return False

    def rightMove(self, mainPPWord, gPatternToApply):

        for numberDep in range(mainPPWord + 1, len(self.parsePointWordList), 1):
            if (self.parsePointWordList[numberDep].parsed):
                if (self.checkInderectDependency(mainPPWord, numberDep) == False):
                    break
            else:
                depWord = self.parsePointWordList[numberDep].word
                morphForm = self.checkWord(depWord, gPatternToApply)
                if (morphForm != None):
                    return (True, numberDep, morphForm)
        return (False, None, None)

    def leftMove(self, mainPPWord, gPatternToApply):
        # Шел с человеком с зонтом(человек с зонтом, т.к. иначе - непроективная конструкция) Важно, чтобы к зонту относилось второе с
        # здесь сложнее, для каждого потенциального зависимого слова(которое уже подтвердили, что модель подходит), ищем, есть ли предлог слева..... - это тааак долго

        for numberDep in range(mainPPWord - 1, -1, -1):
            if (self.parsePointWordList[numberDep].parsed):
                if (self.checkInderectDependency(mainPPWord, numberDep) == False):
                    break
            else:
                depWord = self.parsePointWordList[numberDep].word
                morphForm = self.checkWord(depWord, gPatternToApply)
                if (morphForm != None):  # данное i-слово удовлетворяет требованиям зависимости модели
                    return (True, numberDep, morphForm)
        return (False, None, None)

    def isApplicable(self, mainPPWord, gPatternToApply):  # где проверка предлогов???????
        # mainPPWord - номер главного!!!
        if (ParsePoint.directForIsApplicable > 0):
            (find, numberDep, morphForm) = self.rightMove(mainPPWord, gPatternToApply)
            ParsePoint.directForIsApplicable = -ParsePoint.directForIsApplicable
            if (find):
                return (True, numberDep, morphForm)
            return self.leftMove(mainPPWord, gPatternToApply)
        else:
            (find, numberDep, morphForm) = self.leftMove(mainPPWord, gPatternToApply)
            ParsePoint.directForIsApplicable = -ParsePoint.directForIsApplicable
            if (find):
                return (True, numberDep, morphForm)
            return self.rightMove(mainPPWord, gPatternToApply)

    def apply(self, mainPPWord, dependingPPWord, usedMorphAnswer, gPatternToApply, maxNumberPoint):
        '''create and return new child ParsePoint'''
        newWordList = copy.deepcopy(self.parsePointWordList)
        newWordList[dependingPPWord].parsed = True
        newWordList[dependingPPWord].usedMorphAnswer = usedMorphAnswer
        newGp = Gp(gPatternToApply, self.parsePointWordList[dependingPPWord].word)
        newWordList[mainPPWord].usedGp.append(newGp)
        newMark = self.markParsePoint + math.log(gPatternToApply.mark)
        newParsedList = copy.deepcopy(self.parsed)
        newParsedList.append((mainPPWord, dependingPPWord))
        newNumber = maxNumberPoint + 1
        newAttempts = copy.deepcopy(self.attempts)
        newAttempts.apply()
        newGraph = copy.deepcopy(self.graph)
        depWord = self.parsePointWordList[dependingPPWord].word.word + "_" + str(dependingPPWord)
        mainWord = self.parsePointWordList[mainPPWord].word.word + "_" + str(mainPPWord)
        newGraph.add_node(depWord)
        newGraph.add_edge(mainWord, depWord)
        return ParsePoint(newWordList, [], newMark, self.countParsedWords + 1, newParsedList, newNumber, newAttempts, newGraph)

    def findFirstWord(self, fun, listNumbersVariants, allPatternsListParam):
        numberChildPoint = self.numberPoint + 1
        for i in range(len(self.parsePointWordList)):
            curPointWord = self.parsePointWordList[i]
            listNewParsePoints = []
            for j in range(len(curPointWord.word.morph)):
                curMorph = curPointWord.word.morph[j]
                if fun(curMorph):
                    newWordList = copy.deepcopy(self.parsePointWordList)
                    newWordList[i].parsed = True
                    newWordList[i].usedMorphAnswer = copy.deepcopy(curMorph)
                    curListNumberVariants = copy.deepcopy(listNumbersVariants)
                    curListNumberVariants = list(filter(lambda x:x[0] != i, curListNumberVariants))
                    patternsCurVariant = newWordList[i].word.gPatterns[j]
                    att = Attempts(i, patternsCurVariant, curListNumberVariants, allPatternsListParam)
                    g = nx.DiGraph()# хранится граф (networkx)
                    newNodeName = curPointWord.word.word + "_" + str(i)
                    g.add_node(newNodeName)
                    newParsePoint = ParsePoint(newWordList, [], 0, 1, [], numberChildPoint, att, g)
                    numberChildPoint += 1
                    listNewParsePoints.append(newParsePoint)
            if listNewParsePoints:
                return (listNewParsePoints, [i])
        return None

    def getNewParsePoint(self, maxNumberPoint):
        '''create new ParsePoint, child for self'''
        while True:
            ans = self.attempts.get()
            if ans == None:
                return None
            (potMain, potPattern, potDep, potDepParseVariant) = ans
            depWord = self.parsePointWordList[potDep].word
            if self.checkWord(depWord, potDepParseVariant, potPattern):
                usedDepMorph = depWord.morph[potDepParseVariant]
                newParsePoint = self.apply(potMain, potDep, usedDepMorph, potPattern, maxNumberPoint)
                self.childParsePoint.append(newParsePoint)
                self.attempts.next()
                return (newParsePoint, potPattern)
            self.attempts.next()


    def checkEndParse(self):
        '''check that all words in this ParsePoint are parsed'''
        # вроде достаточно проверять self.attempts.flagEnd
        for curPointWord in self.parsePointWordList:
            if (curPointWord.parsed == False):
                return False
        return True

    def checkPrep(self):
        for i in range(len(self.parsePointWordList)):
            curMain = self.parsePointWordList[i]
            if curMain.usedMorphAnswer.s_cl == 'preposition':
                if not curMain.usedGp: # у предлога нет зависимого
                    return False
                if len(curMain.usedGp) > 1: # у предлога больше одного зависимого
                    return False
                curDep = curMain.usedGp[0].depWord
                if curDep.numberInSentence <= i: # у предлога зависимое должно стоять справа от главного
                    return False
        return True

    def visualizate(self, name = ""):
        global numberWindows
        numberWindows += 1
        fig = plt.figure(numberWindows)
        pos = graphviz_layout(self.graph, prog='dot')
        x_values, y_values = zip(*pos.values())
        x_max = max(x_values)
        x_min = min(x_values)
        x_margin = (x_max - x_min) * 0.25
        plt.xlim(x_min - x_margin, x_max + x_margin)
        y_max = max(y_values)
        y_min = min(y_values)
        y_margin = (y_max - y_min) * 0.25
        plt.ylim(y_min - y_margin, y_max + y_margin)
        fig.canvas.mpl_connect('button_press_event', lambda event: onMouseClickParsePoint(event, self, pos))
        nx.draw(self.graph, pos, with_labels=True, arrows=False, node_size=1, horizontalalignment='center',
                verticalalignment='top', font_size=20)
        if name:
            plt.title(name)
        else:
            plt.title(self.__repr__())
        plt.show()

def onMouseClickParsePoint(event, parsePoint, pos):
    # type: (matplotlib.backend_bases.MouseEvent) -> None
    # Координаты клика в системе координат осей
    x = event.xdata
    y = event.ydata
    near_word = ""
    min_dist_2 = 100000000000
    for (word, (x_word, y_word)) in pos.items():
        cur_dist_2 = (x_word - x) ** 2 + (y_word - y) ** 2
        if cur_dist_2 < min_dist_2:
            near_word = word
            min_dist_2 = cur_dist_2
    wordBorder = near_word.rfind('_')
    numberWord = int(near_word[wordBorder+ 1:])
    textWord = near_word[:wordBorder]
    w = textWord + ' - ' + parsePoint.parsePointWordList[numberWord].usedMorphAnswer.__repr__()
    global numberWindows
    numberWindows += 1
    plt.figure(numberWindows, figsize=(0.5 + 0.12 * len(w),0.5)) # потом сделать возможность нескольких окон
    plt.axis('off')
    plt.text(0, 0.5, w, size = 15)
    plt.show()


class Sentence:
    def __init__(self):
        self.inputStr = ""
        self.wordList = []
        self.rootPP = None  # заполняется потом, с помощью getRootParsePoint
        self.firstParseWordsIndices = []  # слова, первые для разбора, в простых предложениях
        self.bestParsePoints = [] # хранится список точек разбора, упорядоченных по убыванию оценки
        self.listNumberWords = [] # хранится список элементов вида [(номер слова, номер варианта его разбора )]
        self.graph = nx.DiGraph()# хранится граф (networkx)
        self.maxNumberParsePoint = 0
        self.dictParsePoints = {} # словарь соответствия названия точки разбора и точки разбора
        self.allPatternsList = []
        # список вида [[модели управления]], для каждого варианта разбора каждого слова храним его возможные модели управления
        # j элементе i элемента allPatternsList - список моделей управления для j варианта разбора i слова

    def __repr__(self):
        return self.inputStr

    def setString(self, inputStr1):
        self.inputStr = inputStr1
        # слово в предложении - все, отделенное пробелом, точкой, ? ! ...(смотрим только на первую .)
        #: ; " ' началом предложения, запятой, (   ) тире вообще не учитываем(оно отделено пробелами),
        # дефис только в словах очень-очень и тп,
        punctuation = [' ', '.', '?', '!', ':', ';', '\'', '\"', ',', '(', ')']
        curWord = ""
        numberWord = 0
        for i in self.inputStr:
            if (i in punctuation):
                if (len(curWord) != 0):
                    self.wordList.append(Word(curWord.lower(), numberWord))
                    numberWord += 1
                    curWord = ""
            elif (i != '-' or (len(curWord) != 0)):  # - и непустое слово -  это дефис
                curWord = curWord + i
        if (len(curWord) != 0):
            self.wordList.append(Word(curWord.lower(), numberWord))

    def morphParse(self):
        for curWord in self.wordList:
            curListNumbersVariants = curWord.morphParse()
            self.listNumberWords += curListNumbersVariants

    def getGPatterns(self, con):
        for curWord in self.wordList:
            listPatternsForVariants = curWord.getGPatterns(con)
            self.allPatternsList.append(listPatternsForVariants)

    def getRootParsePoint(self):
        self.rootPP = ParsePoint([], [], 0.0, 0, [], 0, None, None)
        rootName = self.rootPP.__repr__()
        self.graph.add_node(rootName)
        self.dictParsePoints[rootName] = self.rootPP
        for word in self.wordList:
            curParsePointWord = ParsePointWord()
            curParsePointWord.parsed = False
            curParsePointWord.word = word
            self.rootPP.parsePointWordList.append(curParsePointWord)
        verbRes = self.rootPP.findFirstWord(lambda m: m.s_cl == 'verb', self.listNumberWords, self.allPatternsList)
        if verbRes:
            (listNewParsePoints, firstWords) = verbRes
        else:
            # в предложении нет глагола
            nounRes = self.rootPP.findFirstWord(lambda m: m.s_cl == 'noun' and m.case_morph == 'nominative', self.listNumberWords, self.allPatternsList)
            if nounRes:
                (listNewParsePoints, firstWords) = nounRes
            else:
                prepRes = self.rootPP.findFirstWord(lambda m: m.s_cl == 'preposition', self.listNumberWords, self.allPatternsList)
                if prepRes:
                    (listNewParsePoints, firstWords) = prepRes
                else:
                    print("В предложении нет глагола, сущ в И.п, предлога")
                    sys.exit()
        self.rootPP.childParsePoint = listNewParsePoints
        self.maxNumberParsePoint = len(listNewParsePoints) # есть корневая точка и len(listNewParsePoints) ее дочерних,
        self.firstParseWordsIndices = firstWords
        self.bestParsePoints = listNewParsePoints
        for curChild in listNewParsePoints:
            childName = curChild.__repr__()
            self.graph.add_node(childName)
            self.graph.add_edge(rootName, childName, n = "")
            self.dictParsePoints[childName] = curChild

    def insertNewParsePoint(self, newPoint):
        '''insert new ParsePoint into bestParsePoints'''
        self.bestParsePoints.insert(0, newPoint)

    def getBestParsePoint(self):
        return self.bestParsePoints[0]

    # проверка связности - считаем, сколько слов в связном дереве, если = кол-ву слов, то все ок
    # на вход - res(т.е. bestParsePoint)
    def countDependent(self, curParsePoint, firstWordIndex):
        newParsePointWord = curParsePoint.parsePointWordList[firstWordIndex]
        count = 1
        for curModel in newParsePointWord.usedGp:
            depWord1 = curModel.depWord
            # print(depWord1.word)
            count += self.countDependent(curParsePoint, depWord1.numberInSentence)
        return count

    def checkConnectivity(self, curParsePoint):  # параметр - предложение
        return len(self.wordList) == self.countDependent(curParsePoint, self.firstParseWordsIndices[0])


    def visualizate(self):
        '''visualizate tree of parse'''
        global numberWindows
        numberWindows += 1
        fig = plt.figure(numberWindows)
        pos = graphviz_layout(self.graph, prog='dot')
        x_values, y_values = zip(*pos.values())
        x_max = max(x_values)
        x_min = min(x_values)
        x_margin = (x_max - x_min) * 0.25
        plt.xlim(x_min - x_margin, x_max + x_margin)
        y_max = max(y_values)
        y_min = min(y_values)
        y_margin = (y_max - y_min) * 0.25
        plt.ylim(y_min - y_margin, y_max + y_margin)
        fig.canvas.mpl_connect('button_press_event', lambda event: onMouseClickTree(event, self.dictParsePoints, pos))
        nx.draw_networkx_nodes(self.graph, pos, node_size=500, with_labels = True, node_color = 'silver')
        nx.draw(self.graph, pos, with_labels=True, arrows=False, node_size=1, horizontalalignment='center',
                verticalalignment='top', font_size=10, font_color='b')
        grafo_labels = nx.get_edge_attributes(self.graph, 'n')
        nx.draw_networkx_edge_labels(self.graph, pos, font_size=10, edge_labels = grafo_labels, label_pos=0.5, rotate = False)
        plt.title(self.__repr__())
        plt.show()



    def sintParse(self):
        if (not self.rootPP):
            self.getRootParsePoint()

        while (1):
            bestParsePoint = self.getBestParsePoint()
            #bestParsePoint.visualizate(self.firstParseWordsIndices, "Лучшая точка")
            res = bestParsePoint.getNewParsePoint(self.maxNumberParsePoint)
            print(res)
            if (res == None):
                print("Не разобрано!")
                return bestParsePoint
            else:
                (newPoint, pattern) = res
                self.maxNumberParsePoint += 1
                newPointName = newPoint.__repr__()
                self.graph.add_node(newPointName)
                self.graph.add_edge(bestParsePoint.__repr__(), newPoint.__repr__(), n = pattern.__repr__())
                self.dictParsePoints[newPointName] = newPoint
                self.insertNewParsePoint(newPoint)
                #newPoint.visualizate(self.firstParseWordsIndices, "Новая точка")
                if newPoint.checkEndParse():
                    if newPoint.checkPrep():
                        return newPoint

def onMouseClickTree(event, dictParsePoints, pos):
    # type: (matplotlib.backend_bases.MouseEvent) -> None
    axes = event.inaxes

    # В качестве текущих выберем оси, внутри которых кликнули мышью
    plt.sca(axes)

    # Координаты клика в системе координат осей
    x = event.xdata
    y = event.ydata

    near_point = ""
    min_dist_2 = 100000000000
    for (word, (x_word, y_word)) in pos.items():
        cur_dist_2 = (x_word - x) ** 2 + (y_word - y) ** 2
        if cur_dist_2 < min_dist_2:
            near_point = word
            min_dist_2 = cur_dist_2
    dictParsePoints[near_point].visualizate()
    plt.show()

numberWindows = 0

class WordResult:
    def __init__(self, p, mf, w, gps):
        self.parsed = p
        self.morfForm = mf
        self.word = w
        self.usedGPatterns = gps

    def __repr__(self):
        if self.parsed:
            return self.word + ":" + self.morfForm.__repr__()
        return "Не разобрано"

def parse(con, str1, needTrace=False):
    s = Sentence()
    s.setString(str1)
    s.morphParse()
    s.getGPatterns(con)
    res = s.sintParse()
    if (needTrace):
        s.visualizate() # визуализация дерева построения
    res.visualizate(str1)
    ans = []
    for curWord in res.parsePointWordList:
        curResult = WordResult(curWord.parsed, curWord.usedMorphAnswer, curWord.word.word, curWord.usedGp)
        ans.append(curResult)
    return ans


con = psycopg2.connect(dbname='gpatterns', user='postgres',
                       password='postgres', host='localhost')
#str1 = "Идете домой с братом." Жуть
#str1 = "Идите с братом домой." # с - почему-то существительное...
str1 = "Русская армия готовилась к сражению."

#str1 = "Ходить на работу."
#str1 = "Бабушка снова взяла сумку."

#str1 = "С родителями горжусь братом."

#str1 = "Будете пить сок?"
#str1 = "Будете сок?"

#str1 = "Ходить на работу."

#str1 = "Взрослые люди ходят на работу."

a1 = parse(con, str1, True)
for i in a1:
    print(i)

#str1 = "Взрослые ходят на интересную работу."

#str1 = "Быстро идите с братом домой ."
#str1 = "Из ворот вышли две тетушки с сумками."
#str1 = "Над заборами обвисали гроздья сирени"
#a1 = parse(con, "Студенты замерзли на лекции.", True)

#a1 = parse(con, "Заяц поздней осенью меняет серую шубу на белую.", True)

#a1 = parse(con, str1, True)
'''
a1 = parse(con, "Я прочел до середины список кораблей.", True)
a1 = parse(con, "Вязнут расписные спицы в расхлябанные колеи.", True)
a1 = parse(con, "Ковыли с вековою тоскою пригнулись к земле.", True)
a1 = parse(con, "К метро шли долго.", True)
a1 = parse(con, "Студенты замерзли на лекции.", True)
a1 = parse(con, "Ты стал очень хорошим человеком.", True)


a1 = parse(con, "Ты будешь сок?", True)
a1 = parse(con, "Все счастливые семьи счастливы по-своему.", True)
a1 = parse(con, "Осень поражает нас своими непрерывными изменениями.", True)
a1 = parse(con, "Вещи, потерянные нами,c обязательно вернутся к нам!.", True)


a1 = parse(con, "Моя ладонь превратилась в кулак.", True)

a1 = parse(con, "Счастье можно найти даже в темные времена.", True)

a1 = parse(con, "Дети поздно пришли домой.", True)
a1 = parse(con, "На штурм.", True)
print(a1)
'''
'''a1 = parse(con, "Ходить на работу.")
a1 =  parse(con, "Маленький мальчик хочет спать.",  True)
s = Sentence()
str1 = "Взрослые люди ходят на работу."
s.setString(str1)
s.morphParse()
s.getGPatterns(con)
res = s.sintParse()
res.visualizate(s.firstParseWordsIndices)
for i in range(10):
    res1 = s.sintParse()
    res1.visualizate(s.firstParseWordsIndices)
a1 = parse(con, "Маленький мальчик хочет спать.")
a1 = parse(con, "Каждый час имеет свое чудо.", True)
a1 = parse(con, "Памятник себе воздвиг нерукотворный.", True)
a1 = parse(con, "Рассеет серых туч войска.", True)
#a1 = parse(con, "Сегодня будет четный день.", True)
a1 = parse(con, "Шекспир был английским писателем.", True)
a1 = parse(con, "Надежда умирает последней.", True)
a1 = parse(con, "В небе танцует золото.", True)
a1 = parse(con, "Звезды.", True)
'''

# a1 = parse(con, "Взрослые люди ходят на работу.", True)

# a1 = parse(con, "Приведет за собой весну.", True) плохо
# a1 = parse(con, "Взрослые люди ходят на работу.", True) плохо
# a1 = parse(con, "Заяц поздней осенью меняет серую шубу на белую.", True)
# a1 = parse(con, "Я прочел до середины список кораблей.", True)
# a1 = parse(con, "Вязнут расписные спицы в расхлябанные колеи.", True)
# a1 = parse(con, "Ковыли с вековою тоскою пригнулись к земле.", True)
# a1 = parse(con, "К метро шли долго.", True)
# a1 = parse(con, "Студенты замерзли на лекции.", True)
# a1 = parse(con, "Ты стал очень хорошим человеком.", True)


# a1 = parse(con, "Ты будешь сок?", True)
# a1 = parse(con, "Все счастливые семьи счастливы по-своему.", True)
# a1 = parse(con, "Осень поражает нас своими непрерывными изменениями.", True)
# a1 = parse(con, "Вещи, потерянные нами,c обязательно вернутся к нам!.", True)


# a1 = parse(con, "Моя ладонь превратилась в кулак.", True) плохо

# a1 = parse(con, "Счастье можно найти даже в темные времена.", True) плохо

# a1 = parse(con, "Дети поздно пришли домой.", True)  плохо
# a1 = parse(con, "На штурм.", True)  плохо главное дб НА

#a1 = parse(con, "Принесет с собой.", True)
#a1 = parse(con, "Приведет с собой.", True)

# print(a1)