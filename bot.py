import asyncio
import logging
from aiogram import Bot, Dispatcher, types, html
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove
from random import randint
from aiogram import F
import re
from db import Database
from config import TOKEN

import text

db = Database("1.db")

db.create_table()

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token="", parse_mode="HTML")
# Диспетчер
dp = Dispatcher()

class GrechkinTestStorage(StatesGroup):
    name = State()
    email = State()
    phone = State()
    test = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(text.start)

@dp.message(Command("test"))
async def cmd_food(message: types.Message, state: FSMContext):
    await message.answer(
        text="Выберите ваше имя:",
    )
    # Устанавливаем пользователю состояние "вводит имя"
    await state.set_state(GrechkinTestStorage.name)

#введено имя, просим ввести телефон
@dp.message(GrechkinTestStorage.name, F.text)
async def name_entered(message: types.Message, state: FSMContext):
    await state.update_data(users_name = message.text)
    await message.answer(text="Ваш номер телефона (только цифры, начиная с восьмёрки):")
    await state.set_state(GrechkinTestStorage.phone)

#введён телефон, просим ввести e-mail
@dp.message(GrechkinTestStorage.phone, F.text)
async def phone_entered(message: types.Message, state: FSMContext):
    if not (message.text.startswith('8') and len(message.text) == 11 and int(message.text)):
        await bot.send_message(message.from_user.id, "Некорректный телефон, попробуйте снова")
        return

    await state.update_data(users_phone = message.text)
    await message.answer(text="Ваш e-mail:")
    await state.set_state(GrechkinTestStorage.email)

# введён e-mail, начинаем тест    
@dp.message(GrechkinTestStorage.email, F.text)
async def name_entered(message: types.Message, state: FSMContext):


    pattern = r"^[-\w\.]+@([-\w]+\.)+[-\w]{2,4}$"
    if not re.findall(pattern, message.text):
        await bot.send_message(message.from_user.id, "Неверный емэйл, попробуйте снова")
        return

    await state.update_data(users_email = message.text)

    # этот хэндлер также отрисовывает интерфейс для первого вопроса
    builder = InlineKeyboardBuilder()
    # счётчик для динамического задания атрибута callback_data
    count = 0
    for answer in text.answers_1:
        count += 1
        builder.add(types.InlineKeyboardButton(text=answer, callback_data=f"answer_{count}"))
    builder.adjust(2)
    # для первого вопроса только кнопка next
    builder.row( 
        types.InlineKeyboardButton(text='➡', callback_data="next")
        )
    # в состояние заноситься номер текущего вопроса
    await state.update_data(current_question = 1)
    # ссылка на обьект сообщения для его последующего удаления
    msg = await message.answer(text.question1, reply_markup=builder.as_markup(resize_keyboard=True))
    await state.update_data(prev_msg = msg)
    # устанавливаем состояние тест для следующего хендлера
    await state.set_state(GrechkinTestStorage.test)

# основной хендлер для воспроизвдения теста
@dp.callback_query(GrechkinTestStorage.test)
async def question(callback: types.CallbackQuery, state: FSMContext):
    # получаем все данные состояния
    user_data = await state.get_data()
    # удаляем прошлое сообщение
    await user_data['prev_msg'].delete()
    # получаем номер текущего вопроса в переменную c_q
    c_q = user_data['current_question']

    # проверяем есть ли отмеченные ответы при нажатии на кнопку next
    if callback.data == 'next':
        try:
            users_answers = user_data[f'number_{c_q}']
        except KeyError:
            users_answers = set()
        # если ответы есть переходим к следующему вопросу
        if users_answers != set():
            c_q += 1 
    elif callback.data == 'previos':
        c_q -= 1

    # проверяем наличие ответов клиента и при нажатии на кнопки ответов
    try:
        users_answers = user_data[f'number_{c_q}']
    except KeyError:
        users_answers = set()

    # при нажатии на кнопку ответа он добавляется в множество ответов, если его там нет, и удаляется если есть
    if callback.data.startswith('answer'):
        if callback.data in users_answers:
            users_answers.remove(callback.data)
        else:
            # проверяем что ответов не больше чем положенно для текущего вопроса
            if text.answers_limits[text.questions[c_q-1]] > len(users_answers):
                users_answers.add(callback.data)
            
        # результат заносим в state
        await state.update_data({f'number_{c_q}':users_answers})
    
    # проверка, если находимся на последнем вопросе, чистим state, и обрабатываем результаты
    if c_q > len(text.qerst_and_dict.keys()):
        data = await state.get_data()
        await results(data, callback.from_user.id)
        await state.clear()
    # в остальных случаях формируем клавиатуру
    else:
        builder = InlineKeyboardBuilder()
        count = 0
        # qerst_and_dict - словарь вида {_вопрос_:_список ответов_}
        for answer in text.qerst_and_dict[text.questions[c_q-1]]:
            count += 1
            # если ответ уже помечен кнопка будет с галкой
            if f'answer_{count}' in users_answers:
                builder.add(types.InlineKeyboardButton(text ='✅ ' + answer, callback_data=f"answer_{count}"))
            else:
                builder.add(types.InlineKeyboardButton(text = answer, callback_data=f"answer_{count}"))
            
        if c_q == 1:
            builder.add(types.InlineKeyboardButton(text='➡', callback_data="next"))
            builder.adjust(2)
        else:
            builder.adjust(2)
            builder.row(
            types.InlineKeyboardButton(text='⬅', callback_data="previos"), 
            types.InlineKeyboardButton(text='➡', callback_data="next")
            )
        msg = await callback.message.answer(text.questions[c_q-1], reply_markup=builder.as_markup(resize_keyboard = True))
        await state.update_data(prev_msg = msg)
        # передаём в state номер текущего вопроса
        await state.update_data(current_question = c_q)
   

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="Действие отменено",
        reply_markup=ReplyKeyboardRemove()
    )

# обработка результата, его вывод и запись в БД
async def results(full_state : dict, id):
    count_inst = 0
    count_pro = 0
    count_ptr = 0
    count_hoz = 0
    count_lmp = 0

    # 1
    if 'answer_1' in full_state['number_1']:
        count_hoz += 1
    if 'answer_2' in full_state['number_1']:
        count_pro += 1
    if 'answer_3' in full_state['number_1']:
        count_ptr += 1
    if 'answer_4' in full_state['number_1']:
        count_inst += 1
    if 'answer_5' in full_state['number_1']:
        count_lmp += 1

    # 2
    if 'answer_1' in full_state['number_2']:
        count_inst += 1
    if 'answer_2' in full_state['number_2']:
        count_hoz += 1
    if 'answer_3' in full_state['number_2']:
        count_pro += 1
    if 'answer_4' in full_state['number_2']:
        count_ptr += 1
    if 'answer_5' in full_state['number_2']:
        count_lmp += 1

    # 3
    if 'answer_1' in full_state['number_3']:
        count_lmp += 1
    if 'answer_2' in full_state['number_3']:
        count_pro += 1
    if 'answer_3' in full_state['number_3']:
        count_inst += 1
    if 'answer_4' in full_state['number_3']:
        count_hoz += 1
    if 'answer_5' in full_state['number_3']:
        count_ptr += 1

    # 4
    if 'answer_1' in full_state['number_4']:
        count_inst += 1
    if 'answer_2' in full_state['number_4']:
        count_pro += 1
    if 'answer_3' in full_state['number_4']:
        count_hoz += 1
    if 'answer_4' in full_state['number_4']:
        count_ptr += 1
    if 'answer_5' in full_state['number_4']:
        count_lmp += 1

    # 5
    if 'answer_1' in full_state['number_5']:
        count_inst += 1
    if 'answer_2' in full_state['number_5']:
        count_pro += 1
    if 'answer_3' in full_state['number_5']:
        count_ptr += 1
    if 'answer_4' in full_state['number_5']:
        count_lmp += 1
    if 'answer_5' in full_state['number_5']:
        count_hoz += 1

    # 6.1
    if 'answer_1' in full_state['number_6']:
        count_lmp += 1

    # 6.2
    if 'answer_1' in full_state['number_7']:
        count_pro += 1
    
    # 6.3
    if 'answer_1' in full_state['number_8']:
        count_inst += 1

    # 6.4
    if 'answer_1' in full_state['number_9']:
        count_lmp += 1

    # 6.5
    if 'answer_1' in full_state['number_10']:
        count_ptr += 1

    # 6.6
    if 'answer_1' in full_state['number_11']:
        count_inst += 1

    # 6.7
    if 'answer_1' in full_state['number_12']:
        count_pro += 1
    
    # 6.8
    if 'answer_1' in full_state['number_13']:
        count_hoz += 1

    # 6.9
    if 'answer_1' in full_state['number_14']:
        count_lmp += 1

    # 7
    if 'answer_1' in full_state['number_15']:
        count_ptr += 1
    if 'answer_2' in full_state['number_15']:
        count_inst += 1
    if 'answer_3' in full_state['number_15']:
        count_pro += 1
    if 'answer_4' in full_state['number_15']:
        count_lmp += 1

    # 8
    if 'answer_1' in full_state['number_16']:
        count_hoz += 1
    if 'answer_2' in full_state['number_16']:
        count_pro += 1
    if 'answer_3' in full_state['number_16']:
        count_ptr += 1
    if 'answer_4' in full_state['number_16']:
        count_lmp += 1
    if 'answer_5' in full_state['number_16']:
        count_inst += 1

    # 9
    if 'answer_1' in full_state['number_17']:
        count_lmp += 1
    if 'answer_2' in full_state['number_17']:
        count_hoz += 1
    if 'answer_3' in full_state['number_17']:
        count_pro += 1
    if 'answer_4' in full_state['number_17']:
        count_inst += 1
    if 'answer_5' in full_state['number_17']:
        count_ptr += 1

    # 10
    if 'answer_1' in full_state['number_18']:
        count_hoz += 1
    if 'answer_2' in full_state['number_18']:
        count_inst += 1
    if 'answer_3' in full_state['number_18']:
        count_ptr += 1
    if 'answer_4' in full_state['number_18']:
        count_pro += 1
    if 'answer_5' in full_state['number_18']:
        count_lmp += 1

    # 11
    if 'answer_1' in full_state['number_19']:
        count_pro += 1
    if 'answer_2' in full_state['number_19']:
        count_hoz += 1
    if 'answer_3' in full_state['number_19']:
        count_inst += 1
    if 'answer_4' in full_state['number_19']:
        count_lmp += 1
    if 'answer_5' in full_state['number_19']:
        count_ptr += 1

    # 12
    if 'answer_1' in full_state['number_20']:
        count_pro += 1
    if 'answer_2' in full_state['number_20']:
        count_hoz += 1
    if 'answer_3' in full_state['number_20']:
        count_inst += 1
    if 'answer_4' in full_state['number_20']:
        count_lmp += 1
    if 'answer_5' in full_state['number_20']:
        count_ptr += 1

    # 13
    if 'answer_1' in full_state['number_21']:
        count_pro += 1
    if 'answer_2' in full_state['number_21']:
        count_lmp += 1
    if 'answer_3' in full_state['number_21']:
        count_hoz += 1
    if 'answer_4' in full_state['number_21']:
        count_ptr += 1
    if 'answer_5' in full_state['number_21']:
        count_lmp += 1
    if 'answer_6' in full_state['number_21']:
        count_inst += 1

    # 14
    if 'answer_1' in full_state['number_22']:
        count_hoz += 1
    if 'answer_2' in full_state['number_22']:
        count_ptr += 1
    if 'answer_3' in full_state['number_22']:
        count_inst += 1
    if 'answer_4' in full_state['number_22']:
        count_hoz += 1
    if 'answer_5' in full_state['number_22']:
        count_pro += 1
    if 'answer_6' in full_state['number_22']:
        count_lmp += 1

    # 15
    if 'answer_1' in full_state['number_23']:
        count_hoz += 1
    if 'answer_2' in full_state['number_23']:
        count_ptr += 1
    if 'answer_3' in full_state['number_23']:
        count_pro += 1
    if 'answer_4' in full_state['number_23']:
        count_inst += 1
    if 'answer_5' in full_state['number_23']:
        count_hoz += 1
    if 'answer_6' in full_state['number_23']:
        count_pro += 1
    if 'answer_7' in full_state['number_23']:
        count_lmp += 1

    results = [count_inst, count_pro, count_ptr, count_hoz, count_lmp]
    main_motivation = []
    if count_inst == max(results):
        main_motivation.append('Инструментальный')
    if count_pro == max(results):
        main_motivation.append('Профессиональный')
    if count_ptr == max(results):
        main_motivation.append('Патриотический')
    if count_inst == max(results):
        main_motivation.append('Хозяйский')
    if count_lmp == max(results):
        main_motivation.append('Люмпинизированный')
    string = ''
    for i in main_motivation:
        string += f'{i} '

    await bot.send_message(id, text=f'Тест пройден, ваши результы:\nИН:{count_inst} ПР:{count_pro}, ПА:{count_ptr}, ХО:{count_hoz}, ЛЮ:{count_lmp}\nПреобладающий тип/типы мотивации: {string}')
    db.post_test_result(id, full_state['users_name'], full_state['users_email'], int(full_state['users_phone']), count_inst, count_pro, count_ptr, count_hoz, count_lmp)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

