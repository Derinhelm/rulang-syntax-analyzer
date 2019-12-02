from Types import *
from Functions import *
from dbFunctions import *
import copy
import xml.dom.minidom
import pymorphy2
import psycopg2


class InsertElem:
    ''' Храним информацию для вставки в базу для одного слова(главного или зависимого)
    '''
    def __init__(self, morph1, word1, con):
        self.morph = morph1
        self.normWord = word1
        self.numberMorph = str(findOrInsertMorph(con, morph1)) # номер морфа в базе
        self.numberWord = str(findOrInsertWord(con, word1)) # номер слова в базе

class Node:
    def __init__(self, id1, dom1, arrIns):
        self.id = id1
        self.dom = dom1
        self.arrInserts = arrIns # список элемента типа InsertElem



сorporaToImpMorph = {'V':'s_cl', 'NUM':'s_cl', 'PR':'s_cl', 'A':'s_cl', \
                   'ADV':'s_cl', 'CONJ':'s_cl', 'S':'s_cl', 'PART':'s_cl', \
                   'ДЕЕПР':'s_cl', 'ПРИЧ':'s_cl', 'КР':'s_cl', 'СРАВ':'s_cl', 'INTJ':'s_cl', \
                   'ПРЕВ':'s_cl', \
                   'НЕОД':'animate', 'ОД':'animate', \
                   'СРЕД':'gender', 'МУЖ':'gender', 'ЖЕН':'gender', \
                   'ЕД':'number', 'МН':'number', \
                   'ИМ':'case_morph', 'РОД':'case_morph', 'ДАТ':'case_morph', \
                   'ВИН':'case_morph', 'ТВОР':'case_morph', 'ПР':'case_morph', 'МЕСТН':'case_morph', 'ПАРТ':'case_morph', \
                   'НЕСОВ':'perfective', 'СОВ':'perfective', \
                   '3-Л':'person', '2-Л':'person', '1-Л':'person', \
                   'ПРОШ':'tense', 'НАСТ':'tense', 'НЕПРОШ':'tense', 'ИНФ':'tense', \
                   'ИЗЪЯВ':'tense', 'ПОВ':'tense', \
                   'СТРАД':'voice'}

def parseCorporaTag(tagCorpora):
    #возвращает 1. список лямбда-функций, которые надо применить к морфу
    #для проверки на адекватность
    # 2. set важных параметров
    checkFuns = []
    impFeatures = set()
    for curParam in tagCorpora:
    # пока нет ниже 'comparative', 'predicative',
        if curParam == 'V':
            checkFuns.append(lambda m: m.s_cl in ['verb', 'participle', 'shortparticiple', 'gerund'])
        elif curParam == 'S':
            checkFuns.append(lambda m: m.s_cl in ['noun', 'pronoun'])
        elif curParam == 'A':
            checkFuns.append(lambda m: m.s_cl in ['adjective', 'shortadjective', 'number', 'pronoun'])
        #прилагательное: новый, мой, второй
        elif curParam == 'ADV':
            checkFuns.append(lambda m: m.s_cl in ['adverb', 'pronoun'])
        #наречие: плохо, отчасти
        elif curParam == 'NUM':
        #числительное: пять, 2,
            checkFuns.append(lambda m: m.s_cl in ['number'])
        elif curParam == 'PR':
            checkFuns.append(lambda m: m.s_cl in ['preposition'])
        #предлог: в, между, вопреки
        elif curParam == 'CONJ':
            checkFuns.append(lambda m: m.s_cl in ['conjunction', 'pronoun'])
        #союз: и, что, как
        elif curParam == 'PART':
            checkFuns.append(lambda m: m.s_cl in ['particle'])
        #частица: бы, ли, только
        elif curParam == 'INTJ':
            checkFuns.append(lambda m: m.s_cl in ['interjection'])
        #междометие: ого, увы, эх
        elif curParam == 'ИМ':
            checkFuns.append(lambda m: m.case_morph  == 'nominative')
        elif curParam == 'РОД':
            checkFuns.append(lambda m: m.case_morph  == 'genitive')
        elif curParam == 'ДАТ':
            checkFuns.append(lambda m: m.case_morph  == 'dative')
        elif curParam == 'ВИН':
            checkFuns.append(lambda m: m.case_morph  == 'accusative')
        elif curParam == 'ТВОР':
            checkFuns.append(lambda m: m.case_morph  == 'instrumental')
        elif curParam == 'ПР':
            checkFuns.append(lambda m: m.case_morph  == 'prepositional')
        elif curParam == 'ПАРТ':
            checkFuns.append(lambda m: m.case_morph  == 'genitive')
        elif curParam == 'МЕСТН':
            checkFuns.append(lambda m: m.case_morph  == 'prepositional')
        elif curParam == 'ЗВ':
            return ([lambda m: False], None) # с звательным падежом пока не работаем

        elif curParam == 'СРАВ':
            checkFuns.append(lambda m: m.s_cl  == 'comparative')
        elif curParam == 'КР':
            checkFuns.append(lambda m: m.s_cl  == 'shortadjective' or m.s_cl == 'shortparticiple')
        elif curParam == 'NID':
            return ([lambda m: False], None)

        if not curParam in ['СЛ', 'COM', 'СМЯГ', 'НЕСТАНД', 'МЕТА', 'НЕПРАВ']:
            impFeatures.add(сorporaToImpMorph[curParam])
    return (checkFuns, impFeatures)


def eqNormForm(s1, s2, parseS2):
    # равенство начальных форм слов
    # parseS2 - класс для превращения слова, разобранного в pymorphy2, в несов.вид
    if s1 == s2:
        return True
    if (s1 == s2 + "ся"):  # корпус убирает 'ся', pymorphy2 нет
        return True
    if s1.replace("ё", "е") == s2.replace("ё", "е"):
        return True
    s2Impf = parseS2.inflect({'INFN', 'impf'})
    if s2Impf != None and parseS2.tag.POS == 'INFN' and s1 == s2Impf.word:
        # приводим второе слово в несов.вид
        #print(s1, s2)
        return True

    return False


def getParseByPymorphy(curWord, curTagCorpora, curNormalForm, arrParse):
    #print(curWord, curTagCorpora, curNormalForm, arrParse)
    isParsed = False  # был ли хоть один нормальный разбор
    (checkFuns, impFeatures) = parseCorporaTag(curTagCorpora)
    if impFeatures == None: # слово типа NID, 'as-sifr'
        return None
    #print(curWord, curTagCorpora, curNormalForm, arrParse)
    notImpFeat = set(copy.copy(Morph.names)) - impFeatures
    goodParsePymorphy = []
    for curParse in arrParse:
        if eqNormForm(curParse.normal_form, curNormalForm, curParse) or \
                'НЕСТАНД' in curTagCorpora or 'НЕПРАВ' in curTagCorpora or \
                (('VERB' in curParse.tag or 'INFN' in curParse.tag or 'GRND' in curParse.tag or\
                  'PRTF' in curParse.tag or 'PRTS' in curParse.tag) and curTagCorpora[0] == 'V'):
# для глаголов пока не требуем совпадения начальных форм
            m = parseToMorph(curWord, curParse)
            nw = curParse.normal_form #  начальная форма слова
            if m != None:
                flagTrueParse = True
                for curCheckFun in checkFuns:
                    if not curCheckFun(m):
                        flagTrueParse = False
                        break

                if (flagTrueParse):
                    isParsed = True
                    for curField in notImpFeat:
                        setattr(m, curField, 'not_imp')
                    if not m in goodParsePymorphy:
                        curElem = InsertElem(m, nw, con)
                        goodParsePymorphy += [curElem]
    if not isParsed:  # pymorphy2 не дал разбора, удовлетворяющего корпусу, пока не рассматриваем это слово
        #print("Разборы не соответствуют", curWord, curTagCorpora, curNormalForm)
        return None
    return goodParsePymorphy

def parseXML(nameFile, morph):
    doc = xml.dom.minidom.parse(nameFile)
    # а зачем храним id(на всякий случай), вообще-то можно и не хранить, id = index + 1
    arrayParseSentences = []
    parent = doc.getElementsByTagName('S')
    i = 1
    for item in parent:
        newSentence = []
        for child in item.getElementsByTagName('W'): # слова с пробелами пока не учитываем
            if child.getAttribute('LEMMA').count(" ") != 0:
                newNode = Node(child.getAttribute('ID'), child.getAttribute('DOM'), None)
            elif ('0' <= child.getAttribute('LEMMA')[0] <= '9'):
                newNode = Node(child.getAttribute('ID'), child.getAttribute('DOM'), None)
            elif len(child.childNodes) == 0:
                #необычные слова(например, пропущенные и тп)
                # слова, у которых нет значения, т.е. элипсис и одно слово в Grechko.tgt
                newNode = Node(child.getAttribute('ID'), child.getAttribute('DOM'), None)
#<W DOM="5" FEAT="V СОВ ИЗЪЯВ ПРОШ МН" ID="9" LEMMA="ОТВОДИТЬ" LINK="сочин" NODETYPE="FANTOM"/>
            else:
                (id1, dom, feat, word, normWord) =(child.getAttribute('ID'), child.getAttribute('DOM'), \
                           child.getAttribute('FEAT'), \
                           child.childNodes[0].nodeValue, child.getAttribute('LEMMA'))
                word = word.lower().replace("ё", "е").replace(".", "")         # replace(".","") для сокращений
                normWord = normWord.lower().replace("ё", "е").replace(".", "")
                arrParse = morph.parse(word)
                resPymorpy = getParseByPymorphy(word, feat.split(), normWord, arrParse)
                if resPymorpy != None:
                    newNode = Node(id1, dom, resPymorpy)
                else:
                    newNode = Node(child.getAttribute('ID'), child.getAttribute('DOM'), None)
                    print(i, word)
                    print(list(map(lambda x: (getattr(x, 'tag')), arrParse)))
                    print(list(map(lambda x: (getattr(x, 'normal_form')), arrParse)))
                    print(word, normWord, feat)
                    print("-------------------------------------")
            newSentence.append(newNode)

        arrayParseSentences.append(newSentence)
        i += 1
    return arrayParseSentences



def insertPattern3(con, mainMorphNumber, depMorphNumber, \
                  mainWordNumber, depWordNumber):
    cursor = con.cursor()
    comand = "SELECT id FROM gpattern_3_level WHERE " + \
         "main_morph = %s AND dep_morph = %s AND " + \
         "main_word = %s AND dep_word = %s;"
    params = (mainMorphNumber, depMorphNumber, \
            mainWordNumber, depWordNumber)
    cursor.execute(comand, params)
    ind = cursor.fetchall()
    cursor.close()
    cursor = con.cursor()
    if len(ind) == 0:
        comand = "INSERT INTO gpattern_3_level " + \
            "VALUES(DEFAULT, %s, %s, %s, %s, 1);"
        cursor.execute(comand, params)
    else:
        number_gpattern = ind[0][0]
        comand = "UPDATE gpattern_3_level " + \
            "SET mark = mark + 1 WHERE id = %s;"
        cursor.execute(comand, (number_gpattern, ))
    con.commit()
    cursor.close()
def insertPattern2(con, mainMorphNumber, depMorphNumber, \
                  mainWordNumber):
    cursor = con.cursor()
    comand = "SELECT id FROM gpattern_2_level WHERE " + \
         "main_morph = %s AND dep_morph = %s AND " + \
         "main_word = %s;"
    params = (mainMorphNumber, depMorphNumber, \
            mainWordNumber)
    cursor.execute(comand, params)
    ind = cursor.fetchall()
    cursor.close()
    cursor = con.cursor()
    if len(ind) == 0:
        comand = "INSERT INTO gpattern_2_level " + \
            "VALUES(DEFAULT, %s, %s, %s, 1);"
        cursor.execute(comand, params)
    else:
        number_gpattern = ind[0][0]
        comand = "UPDATE gpattern_2_level " + \
            "SET mark = mark + 1 WHERE id = %s;"
        cursor.execute(comand, (number_gpattern, ))
    con.commit()
    cursor.close()

def insertPattern1(con, mainMorphNumber, depMorphNumber):
    cursor = con.cursor()
    comand = "SELECT id FROM gpattern_1_level WHERE " + \
         "main_morph = %s AND dep_morph = %s;"
    params = (mainMorphNumber, depMorphNumber)
    cursor.execute(comand, params)
    ind = cursor.fetchall()
    cursor.close()
    cursor = con.cursor()
    if len(ind) == 0:
        comand = "INSERT INTO gpattern_1_level " + \
            "VALUES(DEFAULT, %s, %s, 1);"
        cursor.execute(comand, params)
    else:
        number_gpattern = ind[0][0]
        comand = "UPDATE gpattern_1_level " + \
            "SET mark = mark + 1 WHERE id = %s;"
        cursor.execute(comand, (number_gpattern, ))
    con.commit()
    cursor.close()

def insertPattern(con, mainMorphNumber, depMorphNumber, \
                  mainWordNumber, depWordNumber, mainMorph, depMorph, mainWord, depWord):
# пока нет проверки на предлог и глагол....
    if mainMorph.s_cl in ['conjunction', 'particle', 'interjection'] or \
        depMorph.s_cl in ['conjunction', 'particle', 'interjection']:
        return # не рассматриваем словосочетания с частицами, союзами и междометиями
    if mainMorph.s_cl == 'preposition':
        print(mainWord, depWord)
        insertPattern2(con, mainMorphNumber, depMorphNumber, \
                       mainWordNumber)
        insertPattern1(con, mainMorphNumber, depMorphNumber)
    elif depMorph.s_cl == 'preposition':
        print(mainWord, depWord)
        insertPattern3(con, mainMorphNumber, depMorphNumber, \
                       mainWordNumber, depWordNumber)
    else:
        print(mainWord, depWord)
        insertPattern3(con, mainMorphNumber, depMorphNumber, \
                      mainWordNumber, depWordNumber)
        insertPattern2(con, mainMorphNumber, depMorphNumber, \
                      mainWordNumber)
        insertPattern1(con, mainMorphNumber, depMorphNumber)

def insertAllPairs(con, mainInserts, depInserts):
# массив номеров слова в таблице word(мб несколько в дальнейшем)
# пока массив из одного элемента
    for curMain in mainInserts:
        for curDep in depInserts:
            mainWord = curMain.normWord
            depWord = curDep.normWord
            mainMorph = curMain.morph
            depMorph = curDep.morph
            mainWordNumber = curMain.numberWord
            depWordNumber = curDep.numberWord
            mainMorphNumber = curMain.numberMorph
            depMorphNumber = curDep.numberMorph
            insertPattern(con, mainMorphNumber, \
                    depMorphNumber,  mainWordNumber, depWordNumber, mainMorph, depMorph, mainWord, depWord)


def insert(nameFile, morph, con):
    arrayParseSentences = parseXML(nameFile, morph)
    #print(arrayParseSentences)
    for curSentence in arrayParseSentences:
        for curWord in curSentence:
            if curWord.dom != '_root':
                mainWord = curSentence[int(curWord.dom) - 1]
                # print(mainWord.text, curWord.text)
                if curWord.arrInserts and mainWord.arrInserts:
                    insertAllPairs(con, mainWord.arrInserts, curWord.arrInserts)


morph = pymorphy2.MorphAnalyzer()
con = psycopg2.connect(dbname='gpatterns', user='postgres',
                        password='postgres', host='localhost')

nameFiles = ['Algoritm.tgt', 'Alpinizm.tgt', 'Andrei_Ashkerov.tgt', 'Anketa.tgt', 'Antiterror.tgt', 'Apraushev.tgt', 'Aprelskie_tezisy_Surkova.tgt', 'Armeniya.tgt', 'Artist_mimansa.tgt', 'Ataka.tgt', 'Ataman_Vikhr.tgt', 'Atlanty_i_atlantologi.tgt', 'Auditory.tgt', 'Avraam_Linkoln.tgt', 'Avtomatizatsiya.tgt', 'A_on_myatezhnyi.tgt', 'Baklanov.tgt', 'Banan.tgt', 'Bankovskii_krizis.tgt', 'Batareika.tgt', 'Beg_po_krugu.tgt', 'Bessonnitsa.tgt', 'Bezrabotnye.tgt', 'Bezrybie.tgt', 'Bez_epokhi.tgt', 'Demonstratsiya_flaga.tgt', 'Ditya_20_siezda.tgt', 'Dobretsov.tgt', 'Doktor_Z.tgt', 'Dolgovaya_vyshka.tgt', 'Dom_pod_solntsem.tgt', 'Donbass.tgt', 'Doroga_v_nikuda.tgt', 'Drakony.tgt', 'Dvadtsat_let_spustya.tgt', 'Dvesti_let.tgt', 'Dvigatel.tgt', 'Dvoe_v_dekabre.tgt', 'Dvortsovyi_makiyazh.tgt', 'Dvukhprotsentnaya_reforma.tgt', 'EGE.tgt', 'Ekonomicheskii_rost.tgt', 'Ekonomisty.tgt', 'Ekspluatatsiya_elity.tgt', 'Ekstremizm.tgt', 'Khudozhestvennaya_gimnastika.tgt', 'Kitaiskii_krossword.tgt', 'Kobzon.tgt', 'Kodeks_molchaniya.tgt', 'Kolchak.tgt', 'Kollaider.tgt', 'Kolybel.tgt', 'Kompartii.tgt', 'Komu_dostanetsya_Chingiskhan.tgt', 'Konkurs_otmenyaetsya.tgt', 'Kooperativ_Lavka.tgt', 'Kooperativ_u_ozera.tgt', 'Korp_210.tgt', 'Korp_220.tgt', 'Korp_230.tgt', 'Korp_240.tgt', 'Korp_250.tgt', 'Pervyi_avtomobil.tgt', 'Pessimist_platit_dvazhdy.tgt', 'Petrushka.tgt', 'Piramida.tgt', 'Pirat.tgt', 'Piterskaya_model.tgt', 'Planerizm.tgt', 'Plan_razvitiya_vmf.tgt', 'Plastikovaya_krepost.tgt', 'Platno.tgt', 'Plesnite_koldovstva.tgt', 'Plody_alternativnogo_prosveshcheniya.tgt', 'Po-nashemu.tgt', 'Pochemu_my_ne_s_nimi.tgt', 'Podarok_dlya_vsekh.tgt', 'Podkormlennyi_natsizm.tgt', 'Podstava_na_ekzamene.tgt', 'Politicheskaya_zavisimost.tgt', 'Porazhenie.tgt', 'Pora_stavit_zadachi.tgt', 'Poroshenko_dolzhen_pobedit.tgt', 'Portret_Fridy.tgt', 'Poslednee_vystuplenie_prezidenta.tgt', 'Poslednie_russkie.tgt', 'Poslednii_dovod_issledovatelya.tgt', 'Poslednyaya_taina.tgt', 'Biologiya.tgt', 'Chelovek_oshibka_prirody.tgt', 'Delit_na_vosem.tgt', 'Ekzamen.tgt', 'Gematologiya.tgt', 'Istoriya_tualeta.tgt', 'Khranilishcha.tgt', 'Korp_261.tgt', 'Korp_612.tgt', 'Korp_702.tgt', 'Kovka.tgt', 'Lunnye_kamni.tgt', 'Metis.tgt', 'Na_levom_flange.tgt', 'Novyi_levyi.tgt', 'Osoboe_mnenie.tgt', 'Perestanovka_mebeli.tgt', 'Posledstviya_krizisa-1.tgt', 'Propoved_na_zadannuyu_temu.tgt', 'Rtut.tgt', 'Spam.tgt', 'Terpenie_lopnulo.tgt', 'Tsennosti.tgt', 'Uteshenie.tgt', 'Vyzov_i_otvet.tgt', 'Ya_09.tgt', 'Ya_27.tgt', 'Ya_47.tgt', 'Ya_76.tgt', 'Spasenie_evro.tgt', 'Spiski_Shindlerov.tgt', 'Sputniki.tgt', 'Srednii_klass.tgt', 'Stalingrad.tgt', 'Stalin_vozvrashchyalsya.tgt', 'Status_VShE.tgt', 'Stipendiat.tgt', 'Stolknovenie_Vermeer.tgt', 'Strakhovanie_vkladov_1.tgt', 'Strakhovanie_vkladov_2.tgt', 'Stranitsy_voennoi_istorii.tgt', 'Strast_dushi.tgt', 'Stylaya_krov.tgt', 'Sudu_pomogayut.tgt', 'Sumerki_rossiiskoi_korruptsii.tgt', 'Suverennaya_mutatsiya.tgt', 'Svechenie_Venery.tgt', 'Sverkhkorotkoe_vremya.tgt', 'Sverkhnovaya_2.tgt', 'Sverkhnovaya_ekonomika.tgt', 'Sverzhenie_svetskogo_stroya.tgt', 'Syuzhet.tgt', 'Taezhnyi_ofshor.tgt', 'Taina_zakovannaya_v_led.tgt', 'Taktika_melkikh_shchelchkov.tgt', 'Tarifnaya_viselitsa.tgt', 'Tekhnologii.tgt', 'Tele.tgt', 'Teorema_Stolypina.tgt', 'Nebesnye_formatsii.tgt', 'Nedouchenie.tgt', 'Neftyanye_kacheli.tgt', 'Neiron.tgt', 'Nekhvatka_spetsialistov.tgt', 'Nekommercheskie_organizatsii.tgt', 'Nelegalnaya_perepis.tgt', 'Nelegalnye_kholodilniki.tgt', 'Nelishnyaya_formalnost.tgt', 'Nelzya_sebya_delit.tgt', 'Nepodiemnyi_kredit.tgt', 'Nepotoplyaemye.tgt', 'Neudachnye_vremena.tgt', 'Nezhilye_pomeshcheniya.tgt', 'Ne_mogu_bolshe_molchat.tgt', 'Ne_nado_vozvrashchatsya_k_Yalte.tgt', 'Nichego_chelovecheskogo.tgt', 'Nobelevskie_premii.tgt', 'Novaya_model_obrazovaniya.tgt', 'Novaya_russkaya_ruletka.tgt', 'Novye_neformaly.tgt', 'Vash_personalnyi_nimb.tgt', 'Velikaya_neftegazovaya.tgt', 'Velikaya_pochinka.tgt', 'Veter.tgt', 'Vinnyi_kamen.tgt', 'Vladimir_Vladimirovich.tgt', 'Vneshnyaya_politika.tgt', 'Voennaya_doktrina.tgt', 'Voennoe_bessilie.tgt', 'Voina_vozrastov.tgt', 'Vozvrashchenie_dollara.tgt', 'Vremya_torgovli.tgt', 'Vse_molchat.tgt', 'Vse_vozrastu_pokorny.tgt', 'Vspolokhi.tgt', 'Vtoraya_popytka.tgt', 'Vysokie_tekhnologii.tgt', 'Vysota.tgt', 'Vysshaya_Shkola_Ekonomiki.tgt', 'Vyzhivshii_kamikadze.tgt', 'Proryvy_goda.tgt', 'Protorgovavshiesya.tgt', 'Pryamoi_ukol.tgt', 'Psevdoobrazovanie.tgt', 'Pushka.tgt', 'Pust_dolgim_budet_razgovor.tgt', 'Putin_idet_na_ty.tgt', 'Putin_vzyal_kurs_na_agressivnoe_uderzhanie_status-kvo.tgt', 'Pylesos.tgt', 'Rabotat_nekomu.tgt', 'Radioastron.tgt', 'Raspad_SNG.tgt', 'Razvedka.tgt', 'Razvilka.tgt', 'Razvorot_nad_Atlantidoi.tgt', 'Realnaya_politika.tgt', 'Reforma_NDS.tgt', 'Reforma_obrazovaniya.tgt', 'Remni.tgt', 'Rentgen.tgt', 'Repressii.tgt', 'Rezhimnyi_subiekt.tgt', 'Robototekhnika.tgt', 'Roboty.tgt', 'Rodnye_i_priemnye.tgt', 'Rossiiskie_biznes-shkoly.tgt', 'Rossiya_i_VTO.tgt', 'Rossiya_na_evropeiskom_fone.tgt', 'Rossiya_nuzhdaetsya_v_migrantakh.tgt', 'Bionika.tgt', 'Bitov_1.tgt', 'Bitov_2.tgt', 'Bitov_3.tgt', 'Biznes-obrazovanie.tgt', 'Blesnuli_masterstvom.tgt', 'Blokadnoe_detstvo.tgt', 'Bob.tgt', 'Bogi_menyayutsya.tgt', 'Bolezn_rosta.tgt', 'Bolshe_kandidatov.tgt', 'Bolshie_peremeny.tgt', 'Bronya.tgt', 'Budushchee_Medvedeva.tgt', 'Buran.tgt', 'Byt_modnym.tgt', 'Byudzhet.tgt', 'Chelovek_na_tribune.tgt', 'Geroi.tgt', 'Gibridomobil.tgt', 'Glavnaya_taina_nachala_voiny.tgt', 'Gorbachev_Kak_menya_khoronili.tgt', 'Gorodskoe_slonovodstvo.tgt', 'Gosduma_prinyala_zakon_o_kastratsii_pedofilov.tgt', 'Granin.tgt', 'Grechko.tgt', 'Grekhi_ukrainskie.tgt', 'Grekova_1.tgt', 'Grekova_2.tgt', 'Grekova_3.tgt', 'Grisha_Perelman_devyatyi_genii.tgt', 'Gubarev.tgt', 'Igrushki_bogov.tgt', 'Informatsionnoe_obshchestvo.tgt', 'Informtekhnologii.tgt', 'Innovatsionnaya_ekonomika.tgt', 'Interaktiv.tgt', 'Internet-zavisimost.tgt', 'Interviyu_Afanasieva.tgt', 'Interviyu_Dvorkina.tgt', 'Interviyu_Mariny_Astvatsaturyan.tgt', 'Interviyu_Medvedeva.tgt', 'Interviyu_Yavlinskogo.tgt', 'Interviyu_Yurgensa.tgt', 'Istochniki_rosta.tgt', 'Lunokhod.tgt', 'Lyubit_drakona.tgt', 'Lyzhi-1.tgt', 'Lyzhi.tgt', 'Mamleev_Charli.tgt', 'Mamleev_svadba.tgt', 'Manekeny.tgt', 'Mariam_Petrosyan.tgt', 'Marko_Polo.tgt', 'Mars.tgt', 'Mars_1.tgt', 'Mars_2.tgt', 'Mars_3.tgt', 'Martovskaya_revolyutsiya.tgt', 'Maski.tgt', 'Matematika_probok.tgt', 'Mech.tgt', 'Meinert-Ranks.tgt', 'Metallovedenie.tgt', 'Obratnaya_reaktsiya.tgt', 'Obrazovanie_-_novaya_model.tgt', 'Obrazovatelnoe_kreditovanie.tgt', 'Obrushenie_shkoly.tgt', 'Ochishchenie_Olkhona.tgt', 'Oka.tgt', 'Okhota-1.tgt', 'Okhota.tgt', 'Okhotnik_na_palachei.tgt', 'Olenina.tgt', 'On_boitsya_konkurentsii.tgt', 'Opasnaya_blizost.tgt', 'Opasnye_prazdniki.tgt', 'Oppozitsiyu_ne_pustyat.tgt', 'Opravdanie_televideniya.tgt', 'Optimizm.tgt', 'Posledstviya_krizisa.tgt', 'Posledstviya_nezavisimosti.tgt', 'Poslevkusie.tgt', 'Povedenie.tgt', 'Povyshenie_tarifov.tgt', 'Pravda_zalozhnikov.tgt', 'Pravila_igry.tgt', 'Pravilo_75.tgt', 'Pravo_na_dukhovnuyu_pomoshch.tgt', 'Pravo_na_obidu.tgt', 'Prazdnik_obshchei_bedy.tgt', 'Predkrizisnyi_perekur.tgt', 'Predsedatel.tgt', 'Predvybornaya_situatsiya.tgt', 'Preodolet_kompleks_liliputa.tgt', 'Prevratnosti_razvitiya.tgt', 'Prichiny_krizisa.tgt', 'Prilet_ptits.tgt', 'Pritok_kapitala.tgt', 'Privatizatsiya_istorii.tgt', 'Prizyvy_pravitelstva_Zubkova.tgt', 'Pri_popustitelstve_robotov.tgt', 'Problema_vybora.tgt', 'Problemy_obrazovaniya.tgt', 'Problemy_s_khlebom.tgt', 'Prodazha_zemli.tgt', 'Profilnoe_obrazovanie.tgt', 'Prognoz_inflyatsii.tgt', 'Programma_Alfa-Shans.tgt', 'Tokarskaya.tgt', 'Tolkovateli_snov.tgt', 'To_v_zhar_to_v_kholod.tgt', 'Traektoriya_ekologicheskoi_mysli.tgt', 'Transplantatsiya_organov.tgt', 'Transport.tgt', 'Tranzit_14.tgt', 'Tranzit_15.tgt', 'Tranzit_16.tgt', 'Tranzit_17.tgt', 'Tranzit_18.tgt', 'Travin_1.tgt', 'Travin_2.tgt', 'Troitsk_kak_tsentr_novoi_Moskvy.tgt', 'Trudnosti_rosta.tgt', 'Trud_i_kapital.tgt', 'Tselina.tgt', 'V_chem_vinovat_Putin.tgt', 'V_konstitutsii_ne_dolzhno_byt_mesta_dlya_vozhdya.tgt', 'V_ozhidanii_peremen.tgt', 'V_perevode_s_nebesnogo.tgt', 'V_pogone.tgt', 'V_redaktorskom_kresle.tgt', 'V_zashchitu_torgashei.tgt', 'V_zimu_bez_grippa.tgt', 'Yakovlev.tgt', 'Yanin.tgt', 'Ya_01.tgt', 'Ya_02.tgt', 'Ya_03.tgt', 'Ya_04.tgt', 'Ya_05.tgt', 'Ya_06.tgt', 'Rumba.tgt', 'Russkii_dom.tgt', 'Rynok.tgt', 'Sanktsii.tgt', 'Sdavaisya_kto_mozhet.tgt', 'Shakhmaty.tgt', 'Shkola_kapitalizma.tgt', 'Shokovaya_terapiya.tgt', 'Shok_bez_trepeta.tgt', 'Sinie_vorotnichki.tgt', 'Sinkhronnoe_plavanie.tgt', 'sirija.tgt', 'Skiltoi.tgt', 'Skulachev.tgt', 'Sluchai_dlya_zhyuri.tgt', 'Sluzhit_by_rad.tgt', 'Sluzhivaya_kvazinauka.tgt', 'Sluzhivoe_pravo.tgt', 'Sokrashchenie_vuzov.tgt', 'Soldatiki.tgt', 'Somnambula_v_tumane.tgt', 'Son.tgt', 'Sovety_oppoziitsii.tgt', 'ES-ofshor.tgt', 'Esli_by_k_vlasti.tgt', 'Eto_tolko_nachalo.tgt', 'Ezhednevnaya_simfoniya.tgt', 'Facebook.tgt', 'Fantasticheskie_perspektivy.tgt', 'Faraony_sobstvennoi_personoi.tgt', 'Filmy_Timura_Bekmambetova.tgt', 'Final_Ligi_Chempionov.tgt', 'Finansovyi_shtorm.tgt', 'Firma_ne_garantiruet.tgt', 'Fitoterapiya.tgt', 'Fizkultura_i_okolo.tgt', 'Fobos-grunt_gibel_mechty.tgt', 'Formula-1.tgt', 'Foto.tgt', 'Fotograf_Vladimir_Mishukov_Sindrom_Platona.tgt', 'Gadzhety-neudachniki.tgt', 'Gaidar.tgt', 'Galileo_Galilei.tgt', 'Galopom_ot_trollei.tgt', 'Gde_budet_vlast.tgt', 'Gde_zhe_Shliman.tgt', 'Itogi_subboty.tgt', 'Iz-pod_kontrolya.tgt', 'Izobreteno_vo_sne.tgt', 'Iz_pochtovykh_yashchikov.tgt', 'Iz_semeinykh_predanii.tgt', 'I_evro_takoi_molodoi.tgt', 'I_k_nim_ne_zarastet_narodnaya_tropa.tgt', 'I_slepye_prozreyut.tgt', 'Kak_politikov.tgt', 'Kak_sokhranit_gumanitarnuyu_nauku.tgt', 'Kak_voevat_s_lzhenaukoi.tgt', 'Kak_zakupat_dorogostoyashchee_oborudovanie.tgt', 'Kamennyi_roi.tgt', 'Kaprossiya.tgt', 'Karpov-Kasparov.tgt', 'Katastrofa.tgt', 'Katyn.tgt', 'Khidzhaby_ne_zakazyvali.tgt', 'Kholodnaya_voina.tgt', 'Mezhdunarodnaya_olimpiada.tgt', 'MGU.tgt', 'Minfin_protiv_Glazieva.tgt', 'Misha.tgt', \
             'Molodezh.tgt', 'Molodtsy.tgt', 'Monopolizatsiya_kanalizatsii.tgt', 'Moskva_privlekaet_menshe.tgt', 'Mozgi_naprokat.tgt', 'Muzei.tgt', 'Muzhei_ne_obeshchal.tgt', 'Nadpisi_iz_doliny_Inda.tgt', 'Nagibin_1.tgt', 'Nagibin_2.tgt', 'Nagibin_3.tgt', 'Nagibin_4.tgt', 'Nalogovaya_sistema.tgt', 'Nalog_na_tainu.tgt', 'Nano.tgt', 'Narkotiki.tgt', 'Natsionalnaya_assambleya.tgt', 'Nauka.tgt', 'Na_dvukh_voinakh_1.tgt', 'Na_dvukh_voinakh_2.tgt', 'Kriptografiya.tgt', 'Krizis_blizhe.tgt', 'Kruglyi_stol.tgt', 'Krupnaya_kala.tgt', 'Kto_ubil.tgt', 'Kukla_Gitlera.tgt', 'Kulturnye_olimpiitsy.tgt', 'Kvartira_na_depozit.tgt', 'Led.tgt', 'Lego.tgt', 'Lekarstva_ot_ustalosti.tgt', 'Lesorub.tgt', 'Letayushchaya_tarelka.tgt', 'Levyi_povorot.tgt', 'Liberaly_sdayutsya.tgt', 'Literatura.tgt', 'Lozh_i_legitimnost.tgt', 'Otboinyi_molotok.tgt', 'Otkaz_ot_grefa.tgt', 'Otkrytoe_pismo.tgt', 'Otluchenie_tserkvi.tgt', 'Ot_vlasti.tgt', 'O_boikote_Pekina.tgt', 'O_chem_rech.tgt', 'Panyushkin-1.tgt', 'Panyushkin.tgt', 'Paraolimpiitsy.tgt', 'Parlamentskaya_komissiya.tgt', 'Parovoz.tgt', 'Pastukh.tgt', 'pedagogika.tgt', 'Peregrev_ekonomiki.tgt', 'Perekrestok.tgt', 'Peremeny_v_pravitelstve.tgt', 'Pereselenie_na_yug.tgt', 'Tseny_na_produkty.tgt', 'Tseny_na_zerno.tgt', 'Tseny_rastut.tgt', 'Tsilindry_Faraona.tgt', 'Tyurma_britanskoi_korony.tgt', 'Tyurma_dlya_svekrovei.tgt', 'Uchebnik_istorii.tgt', 'Ugroza_deflyatsii.tgt', 'Uidya_iz_skazki.tgt', 'Ukho.tgt', 'Ukroshchenie_stroptivogo_naukograda.tgt', 'Underground.tgt', 'Uroki.tgt', 'Uroki_Nord-Osta.tgt', 'Ustar.tgt', 'Ya_10.tgt', 'Ya_11.tgt', 'Ya_12.tgt', 'Ya_13.tgt', 'Ya_14.tgt', 'Ya_15.tgt', 'Ya_16.tgt', 'Ya_17.tgt', 'Ya_18.tgt', 'Ya_19.tgt', 'Ya_20.tgt', 'Ya_21.tgt', 'Ya_22.tgt', 'Ya_23.tgt', 'Ya_24.tgt', 'Ya_25.tgt', 'Ya_26.tgt', 'Ya_30.tgt', 'Ya_31.tgt', 'Ya_32.tgt', 'Ya_33.tgt', 'Ya_34.tgt', 'Ya_35.tgt', 'Ya_36.tgt', 'Ya_37.tgt', 'Ya_38.tgt', 'Ya_39.tgt', 'Ya_40.tgt', 'Ya_41.tgt', 'Ya_42.tgt', 'Ya_43.tgt', 'Ya_44.tgt', 'Ya_45.tgt', 'Ya_46.tgt', 'Ya_48.tgt', 'Ya_49.tgt', 'Ya_50.tgt', 'Ya_51.tgt', 'Ya_52.tgt', 'Ya_53.tgt', 'Ya_54.tgt', 'Ya_55.tgt', 'Ya_56.tgt', 'Ya_58.tgt', 'Ya_59.tgt', 'Ya_60.tgt', 'Ya_70.tgt', 'Ya_72.tgt', 'Ya_73.tgt', 'Ya_74.tgt', 'Ya_75.tgt', 'Ya_77.tgt', 'Ya_78.tgt', 'Ya_79.tgt', 'Ya_90.tgt', 'Ya_91.tgt', 'Ya_92.tgt', 'Ya_93.tgt', 'Ya_94.tgt', 'Ya_96.tgt', 'Ya_97.tgt', 'Zamoroz.tgt', 'Zanimatelnye_tsifry.tgt', 'Zapretnoe_iskusstvo_2006.tgt', 'Zavaly_Rosobrnadzora.tgt', 'Za_pravoe_delo.tgt', 'Zdorovie_na_zavtra.tgt', 'Zemlya_naiznanku.tgt', 'Zhdet_li_nas_golod.tgt', 'Zheldor.tgt', 'Zhenshchin_uravnyayut.tgt', 'Zhivaya_zemlya.tgt', 'Zhivotnye_mukhi.tgt', 'Zhivut_ne_dlya_radosti.tgt', 'Zhores.tgt', 'Zhurnalistskoe_obrazovanie.tgt', 'Chem_kumushek_schitat.tgt', 'Chernaya_osen.tgt', 'Chernye_dyry.tgt', 'Chistka_v_sporte.tgt', 'Chlenstvo_v_VTO.tgt', 'Chto_budet_posle.tgt', 'Chto_delat_posle_24_dekabrya.tgt', 'Chto_doktor_propisal.tgt', 'Chto_takoe_interesno.tgt', 'Chto_takoe_ukhomor.tgt', 'Chto_v_imeni.tgt', 'Chuvstvo_spravedlivosti.tgt', 'Darts.tgt', 'Davaite_zhit_smelo.tgt', 'Delitsya_vlastiyu.tgt', 'Korp_262.tgt', 'Korp_263.tgt', 'Korp_264.tgt', 'Korp_265.tgt', 'Korp_266.tgt', 'Korp_409.tgt', 'Korp_601.tgt', 'Korp_602.tgt', 'Korp_603.tgt', 'Korp_604.tgt', 'Korp_605.tgt', 'Korp_606.tgt', 'Korp_607.tgt', 'Korp_608.tgt', 'Korp_609.tgt', 'Korp_610.tgt', 'Korp_611.tgt', 'Korp_613.tgt', 'Korp_614.tgt', 'Korp_615.tgt', 'Korp_616.tgt', 'Korp_617.tgt', 'Korp_618.tgt', 'Korp_619.tgt', 'Korp_620.tgt', 'Korp_621.tgt', 'Korp_622.tgt', 'Korp_623.tgt', 'Korp_624.tgt', 'Korp_625.tgt', 'Korp_626.tgt', 'Korp_627.tgt', 'Korp_628.tgt', 'Korp_701.tgt', 'Korp_703.tgt', 'Korp_704.tgt', 'Korp_705.tgt', 'Korp_706.tgt', 'Korp_707.tgt', 'Korp_708.tgt', 'Korp_709.tgt', 'Korp_710.tgt', 'Korp_711.tgt', 'Korp_712.tgt', 'Korp_713.tgt', 'Korp_714.tgt', 'Korp_716.tgt', 'Korp_717.tgt', 'Korp_718.tgt', 'Korp_719.tgt', 'Korp_720.tgt', 'Korp_721.tgt', 'Korp_722.tgt', 'Korp_723.tgt', 'Korp_724.tgt', 'Korp_725.tgt', 'Korp_726.tgt', 'Korrektsiya_mifov.tgt', 'Korrida.tgt', 'Koshki.tgt', 'Kovcheg_Zhana_Vanie.tgt']

#for i in range(5, 20):
for i in range(0, 5):
    name = nameFiles[i]
    print("---------------------------------")
    print(name)
    allName = "all/" + name
#allName = "Prob.tgt"
    manyInserter = insert(allName, morph, con)
