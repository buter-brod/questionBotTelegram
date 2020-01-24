# -*- coding: utf-8 -*-
import config
import telebot
import re

questionsFile = "questions"
stringsFile = "strings"
known_usersFile = "known_users"
userPasswordFile = "user_password"
adminFile = "admin"
setPasswordCommand = "password"


class Info: pass
info = Info()

info.strings = {}
info.questions = {}

info.known_usersIds = []
info.adminId = ""
info.userPassword = ""


class Question:
    def __init__(self, id, text):
        self.id = id
        self.text = text
        self.answers = {}


class Answer:
    def __init__(self, questionId, letter, nextQuestionId, text, replyTxt=None):
        self.letter = letter
        self.questionId = questionId
        self.nextQuestionId = nextQuestionId
        self.text = text
        self.replyTxt = replyTxt


def parseStrings():
    f = open(stringsFile, "r", encoding="utf-8")
    stringsList = f.read().splitlines()
    for line in stringsList:
        colonPos = line.find(':')

        if 0 < colonPos < len(line) - 1:
            id = line[:colonPos]
            text = line[colonPos + 1:]
            info.strings[id] = text


def loadUsers():

    try:
        fUserPassword = open(userPasswordFile, "r")
        info.userPassword = fUserPassword.read()
        fUserPassword.close()
    except FileNotFoundError:
        fUserPassword = open(userPasswordFile, "w+")
        fUserPassword.close()
    try:
        fUsers = open(known_usersFile, "r")
        info.known_usersIds = fUsers.read().split(',')
        fUsers.close()
    except FileNotFoundError:
        fUsers = open(known_usersFile, "w+")
        fUsers.close()
    try:
        fAdmin = open(adminFile, "r")
        info.adminId = fAdmin.read()
        fAdmin.close()
    except FileNotFoundError:
        fAdmin = open(adminFile, "w+")
        fAdmin.close()


def parseQuestions():
    f = open(questionsFile, "r", encoding="utf-8")
    contents = f.read()
    lines = contents.splitlines()

    for line in lines:
        dotInd = line.find('.')
        lastInd = len(line) - 1

        if dotInd == -1 or dotInd == lastInd or dotInd == 0:
            continue

        prefix = line[:dotInd]

        matchQuestion = re.match("^[0-9]+$", prefix)
        matchAnswer = re.match('^([0-9]+)([a-z]?)([0-9]*)$', prefix)

        if not matchQuestion and not matchAnswer:
            continue

        text = line[dotInd + 1:lastInd + 1]

        if matchQuestion:
            qId = prefix
            question = Question(qId, text)
            info.questions[qId] = question
        else:
            sqBracketPos1 = line.find('[')
            sqBracketPos2 = line.find(']')
            postfix = ""
            if sqBracketPos1 != -1 and sqBracketPos1 != lastInd and sqBracketPos2 > sqBracketPos1 + 1:
                postfix = line[sqBracketPos1 + 1:sqBracketPos2]
                text = line[dotInd + 1:sqBracketPos1]

            qId = matchAnswer.group(1)
            letter = matchAnswer.group(2)
            nextQId = matchAnswer.group(3)

            question = info.questions.get(qId)
            if question is None:
                continue

            answer = Answer(qId, letter, nextQId, text, postfix)
            question.answers[letter] = answer


bot = telebot.TeleBot(config.token)

loadUsers()
parseQuestions()
parseStrings()

currQuestionForChat = {}


def gameOver(chatId):

    gameOverTxt = info.strings.get("gameover")
    restartTxt = info.strings.get("restart")

    keyboard = telebot.types.InlineKeyboardMarkup()
    callback_btn = telebot.types.InlineKeyboardButton(text=restartTxt, callback_data="restart")
    keyboard.add(callback_btn)

    bot.send_message(chatId, gameOverTxt, reply_markup=keyboard)


def ask(chatId, qID):
    question = info.questions.get(qID)
    if question is None:
        return

    answers = question.answers

    if answers:
        keyboard = telebot.types.InlineKeyboardMarkup()
        for _, answer in answers.items():
            idWithLetter = answer.questionId + answer.letter
            callback_btn = telebot.types.InlineKeyboardButton(text=answer.text, callback_data=idWithLetter)
            keyboard.add(callback_btn)

        bot.send_message(chatId, question.text, reply_markup=keyboard)
    else:
        bot.send_message(chatId, question.text)
        gameOver(chatId)


def setCurrentQuestionForChat(chatId, qID):

    currQuestionForChat[chatId] = qID
    ask(chatId, qID)


def ask_password(chatId):
    passwordTxt = info.strings.get("password")
    if passwordTxt is not None:
        bot.send_message(chatId, passwordTxt)


@bot.message_handler(commands=['start'])
def onStart(message):

    chatId = message.chat.id

    isAdmin = str(chatId) == info.adminId
    isUser = str(chatId) in info.known_usersIds

    if isAdmin:
        hiAdminTxt = info.strings.get("hiadmin")
        if hiAdminTxt is not None:
            bot.send_message(chatId, hiAdminTxt)

    if isUser or isAdmin:
        send_welcome(message.chat.id)
    else:
        ask_password(chatId)


def send_welcome(chatId):

    currQuestionForChat[chatId] = "1"

    introTxt = info.strings.get("intro")
    if introTxt is not None:
        bot.send_message(chatId, introTxt)

    setCurrentQuestionForChat(chatId, "1")


def checkPassword(chatId, password):

    if password == config.admin_password:
        info.adminId = str(chatId)
        fAdmin = open(adminFile, "w+")
        fAdmin.write(str(info.adminId))
        fAdmin.close()
        return True

    elif password == info.userPassword:
        info.known_usersIds.append(str(chatId))
        fUsers = open(known_usersFile, "w+")
        fUsers.writelines(info.known_usersIds)
        fUsers.close()
        return True

    return False


def setUserPassword(password):
    fUserPassword = open(userPasswordFile, "w+")
    fUserPassword.write(password)
    fUserPassword.close()


@bot.message_handler(content_types=["text"])
def onMessage(message):

    chatId = message.chat.id
    text = message.text

    chatIdStr = str(chatId)

    if text == "forget":

        if chatIdStr in info.known_usersIds:
            info.known_usersIds.remove(chatIdStr)
            fUsers = open(known_usersFile, "w+")
            fUsers.writelines(info.known_usersIds)
            fUsers.close()

        if chatIdStr == info.adminId:
            info.adminId = ""
            fAdmin = open(adminFile, "w+")
            fAdmin.close()

        ask_password(chatId)
        return

    isAdmin = str(chatId) == info.adminId
    isUser = str(chatId) in info.known_usersIds

    needPassword = not (isAdmin or isUser)

    if isAdmin:
        pInd = text.find(setPasswordCommand)
        if pInd == 0 and len(text) > len(setPasswordCommand) + 1:
            newPassword = text[len(setPasswordCommand) + 1:]
            info.userPassword = newPassword
            setUserPassword(newPassword)
            passwordChangedTxt = info.strings.get("passwordChangedTxt")
            bot.send_message(chatId, passwordChangedTxt)

    if needPassword:
        passOk = checkPassword(chatId, text)

        if not passOk:
            wrongPassTxt = info.strings.get("wrongpass")
            bot.send_message(chatId, wrongPassTxt)
            ask_password(chatId)
        else:
            isAdmin = str(chatId) == info.adminId
            if isAdmin:
                hiAdminTxt = info.strings.get("hiadmin")
                if hiAdminTxt is not None:
                    bot.send_message(chatId, hiAdminTxt)

            send_welcome(chatId)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:

        chatId = call.message.chat.id

        if not currQuestionForChat:
            restartedTxt = info.strings.get("restarted")
            bot.send_message(chatId, restartedTxt)

            chatIdStr = str(chatId)

            isAdmin = chatIdStr == info.adminId
            isUser = chatIdStr in info.known_usersIds
            needPassword = not (isAdmin or isUser)

            if needPassword:
                ask_password(chatId)
            else:
                send_welcome(chatId)
            return

        if call.data == "restart":
            send_welcome(chatId)
            return

        idWithLetterMatch = re.match("^([0-9]+)([a-z]+)$", call.data)
        qId = idWithLetterMatch.group(1)
        letter = idWithLetterMatch.group(2)

        questionID = currQuestionForChat.get(chatId)

        if qId != questionID:
            return

        currQuestion = info.questions.get(questionID)
        answer = currQuestion.answers.get(letter)

        if len(answer.replyTxt) > 0:
            bot.send_message(chatId, answer.replyTxt)

        setCurrentQuestionForChat(chatId, answer.nextQuestionId)


if __name__ == '__main__':
    bot.infinity_polling()
