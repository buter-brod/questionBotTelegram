# -*- coding: utf-8 -*-
import config
import telebot
import re

questionsFile = "questions.txt"
stringsFile = "strings.txt"

strings = {}
questions = {}


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
            strings[id] = text


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
            questions[qId] = question
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

            question = questions.get(qId)
            if question is None:
                continue

            answer = Answer(qId, letter, nextQId, text, postfix)
            question.answers[letter] = answer


bot = telebot.TeleBot(config.token)

parseQuestions()
parseStrings()

currQuestionForChat = {}


def gameOver(chatId):

    gameOverTxt = strings.get("gameover")
    restartTxt = strings.get("restart")

    keyboard = telebot.types.InlineKeyboardMarkup()
    callback_btn = telebot.types.InlineKeyboardButton(text=restartTxt, callback_data="restart")
    keyboard.add(callback_btn)

    bot.send_message(chatId, gameOverTxt, reply_markup=keyboard)


def ask(chatId, qID):
    question = questions.get(qID)
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


@bot.message_handler(commands=['start'])
def onStart(message):
    send_welcome(message.chat.id)


def send_welcome(chatId):

    currQuestionForChat[chatId] = "1"

    introTxt = strings.get("intro")
    if introTxt is not None:
        bot.send_message(chatId, introTxt)

    setCurrentQuestionForChat(chatId, "1")


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:

        chatId = call.message.chat.id

        if not currQuestionForChat:
            forgotTxt = strings.get("forgot")
            bot.send_message(chatId, forgotTxt)
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

        currQuestion = questions.get(questionID)
        answer = currQuestion.answers.get(letter)

        if len(answer.replyTxt) > 0:
            bot.send_message(chatId, answer.replyTxt)

        setCurrentQuestionForChat(chatId, answer.nextQuestionId)


if __name__ == '__main__':
    bot.infinity_polling()
