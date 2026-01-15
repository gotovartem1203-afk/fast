import requests
from bs4 import BeautifulSoup
import time
import random
import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime  # Добавьте этот импорт в начало файл

app = FastAPI()

# URL вашей базы данных
DATABASE_URL = "postgresql://dbname_ivt2_user:J8akbuU5Kjo7yh174uVt3F1vy6EtFR4s@dpg-d5eh99ffte5s73aj1300-a.virginia-postgres.render.com/dbname_ivt2"

# Настройка CORS для работы с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- НОВЫЕ МОДЕЛИ ДАННЫХ ДЛЯ АВТОРИЗАЦИИ ---

class UserRegister(BaseModel):
    name: str
    last_name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# --- ИСПРАВЛЕННАЯ МОДЕЛЬ ДАННЫХ (Подстроена под JS) ---

class BookingData(BaseModel):
    user_id: Optional[int] = None 
    destination: str             # Колонка: destination
    departure_date: str          # Колонка: departure_date (ДОБАВЛЕНО)
    train_number: str            # Колонка: train_number
    carriage_type: str           # Колонка: carriage_type
    price: float                 # Колонка: price
    
    # Эти поля нужны только для отправки письма, в БД они не сохраняются
    email: Optional[str] = None
    passenger_fio: Optional[str] = None
    passport: Optional[str] = None


class SearchQuery(BaseModel):
    departure: str
    arrival: str
    date: str

# --- НОВЫЕ ЭНДПОИНТЫ ДЛЯ РАБОТЫ С БД ---

@app.post("/register")
async def register(user: UserRegister):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        existing = await conn.fetchrow("SELECT id FROM users_ticket WHERE email = $1", user.email)
        if existing:
            raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
        
        row = await conn.fetchrow(
            """INSERT INTO users_ticket (name, last_name, email, password) 
               VALUES ($1, $2, $3, $4) RETURNING id, name, last_name, email""",
            user.name, user.last_name, user.email, user.password
        )
        return {"status": "success", "user": dict(row)}
    finally:
        await conn.close()

@app.post("/login")
async def login(user: UserLogin):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT id, name, last_name, email FROM users_ticket WHERE email = $1 AND password = $2",
            user.email, user.password
        )
        if row:
            return {"status": "success", "user": dict(row)}
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    finally:
        await conn.close()

# --- ВАШ ИСХОДНЫЙ ФУНКЦИОНАЛ БЕЗ ИЗМЕНЕНИЙ ---

def send_email(data: BookingData):
    sender_email = "ticketsearch406@gmail.com"
    password = "zlfa zska fhdh vqcy" 

    msg = MIMEMultipart("alternative")
    msg['From'] = f"Ticket Search <{sender_email}>"
    msg['To'] = data.email
    msg['Subject'] = f"Ваш электронный билет на поезд {data.train_number}"

    html_body = f"""
    <html>
    <body style="margin: 0; padding: 0; background-color: #f6f9fc; font-family: 'Segoe UI', Arial, sans-serif;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0">
            <tr>
                <td align="center" style="padding: 20px;">
                    <table width="600" border="0" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                        <tr>
                            <td style="background-color: #1a237e; padding: 30px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 26px; letter-spacing: 1px;">ЭЛЕКТРОННЫЙ БИЛЕТ</h1>
                                <p style="color: #bbdefb; margin: 8px 0 0; font-size: 16px;">Удачной поездки, {data.passenger_fio}!</p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 30px;">
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td style="padding-bottom: 25px; border-bottom: 2px dashed #e0e0e0;">
                                            <div style="font-size: 12px; color: #7f8c8d; text-transform: uppercase; font-weight: bold;">Маршрут</div>
                                            <div style="font-size: 18px; font-weight: bold; color: #2c3e50; margin-top: 5px;">{data.destination}</div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 25px 0;">
                                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                                <tr>
                                                    <td width="50%" style="vertical-align: top;">
                                                        <div style="font-size: 12px; color: #7f8c8d; text-transform: uppercase;">Поезд</div>
                                                        <div style="font-size: 16px; font-weight: bold; color: #2c3e50;">№ {data.train_number}</div>
                                                    </td>
                                                    <td width="50%" style="vertical-align: top;">
                                                        <div style="font-size: 12px; color: #7f8c8d; text-transform: uppercase;">Вагон</div>
                                                        <div style="font-size: 16px; font-weight: bold; color: #2c3e50;">{data.carriage_type}</div>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 20px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #1a237e;">
                                            <div style="font-size: 12px; color: #7f8c8d; margin-bottom: 5px;">ДАННЫЕ ПАССАЖИРА</div>
                                            <div style="font-size: 16px; font-weight: bold; color: #2c3e50;">{data.passenger_fio}</div>
                                            <div style="font-size: 14px; color: #34495e;">Документ: {data.passport}</div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td style="background-color: #f1f3f8; padding: 25px; text-align: center; border-top: 1px solid #e0e0e0;">
                                <div style="font-size: 14px; color: #7f8c8d;">ИТОГО К ОПЛАТЕ</div>
                                <div style="font-size: 32px; font-weight: bold; color: #1a237e; margin-top: 5px;">{data.price} ₽</div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка почты: {e}")
        return False

def clean_price(price_str):
    if not price_str: return None
    price_str = price_str.replace('\xa0', '').replace(' ', '').replace(',', '.')
    cleaned = ""
    dot_found = False
    for char in price_str:
        if char.isdigit(): cleaned += char
        elif char == '.' and not dot_found:
            cleaned += char
            dot_found = True
    try:
        return int(float(cleaned)) if cleaned else None
    except:
        return None

def get_tickets_from_web(city1, city2, date):
    url = f'https://www.ufs-online.ru/kupit-zhd-bilety/{city1}/{city2}?date={date}'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        time.sleep(random.uniform(0.6, 1.3))
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'lxml')
        results = []
        tickets = soup.find_all('div', class_='wg-train-container')

        for idx, ticket in enumerate(tickets):
            train_tag = ticket.find('a', class_='wg-train-info__number-link')
            train_num = train_tag.get_text(strip=True) if train_tag else "Н/Д"

            time_tags = ticket.find_all('span', class_='wg-track-info__time')
            dep_time = time_tags[0].get_text(strip=True) if len(time_tags) > 0 else "--:--"
            arr_time = time_tags[1].get_text(strip=True) if len(time_tags) > 1 else "--:--"

            dirs = ticket.find_all('span', class_='wg-track-info__direction')
            stats = ticket.find_all('span', class_='wg-track-info__station')
            dep_city = dirs[0].get_text(strip=True) if len(dirs) > 0 else ""
            arr_city = dirs[1].get_text(strip=True) if len(dirs) > 1 else ""
            dep_station = stats[0].get_text(strip=True) if len(stats) > 0 else ""
            arr_station = stats[1].get_text(strip=True) if len(stats) > 1 else ""

            route_block = ticket.find('div', class_='wg-train-info__direction')
            if route_block:
                full_route = route_block.get_text(" ", strip=True)
                full_route = full_route.replace(" → ", " → ").replace("  ", " ")
            else:
                full_route = f"{city1.replace('-', ' ').capitalize()} → {city2.replace('-', ' ').capitalize()}"

            prices_dict = {k: "—" for k in ["Базовый", "Эконом", "Эконом+", "Семейный", "Бистро", "Бизнес", "Первый", "Купе-Сьют", "Сидячий", "Плацкарт", "Купе", "СВ", "Люкс"]}
            min_p = 0
            
            for item in ticket.find_all('div', class_='wg-wagon-type__item'):
                t_tag = item.find('div', class_='wg-wagon-type__title')
                p_tag = item.find('span', class_='wg-wagon-type__price-value')
                s_tag = item.find('span', class_='wg-wagon-type__available-seats')
                
                if t_tag and p_tag:
                    title = t_tag.get_text(strip=True).lower()
                    p_int = clean_price(p_tag.get_text(strip=True))
                    s_count = "".join(filter(str.isdigit, s_tag.get_text(strip=True))) if s_tag else "0"
                    
                    if p_int:
                        info = {"price": str(p_int), "seats": s_count}
                        if "базовый" in title: prices_dict["Базовый"] = info
                        elif "эконом +" in title or "эконом+" in title: prices_dict["Эконом+"] = info
                        elif "эконом" in title: prices_dict["Эконом"] = info
                        elif "семейный" in title: prices_dict["Семейный"] = info
                        elif "бистро" in title: prices_dict["Бистро"] = info
                        elif "бизнес" in title: prices_dict["Бизнес"] = info
                        elif "первый" in title: prices_dict["Первый"] = info
                        elif "сьют" in title: prices_dict["Купе-Сьют"] = info
                        elif "сидяч" in title: prices_dict["Сидячий"] = info
                        elif "плацкарт" in title: prices_dict["Плацкарт"] = info
                        elif "купе" in title: prices_dict["Купе"] = info
                        elif "св" in title: prices_dict["СВ"] = info
                        elif "люкс" in title: prices_dict["Люкс"] = info

                        if min_p == 0 or p_int < min_p: min_p = p_int

            results.append({
                "id": idx, "train": train_num, "departure_time": dep_time, "arrival_time": arr_time,
                "dep_city": dep_city, "arr_city": arr_city, "dep_station": dep_station, "arr_station": arr_station,
                "price": min_p if min_p > 0 else "Н/Д", "prices_all": prices_dict, "route": full_route 
            })
        return results
    except Exception as e:
        print(f"Error: {e}")
        return []

@app.post("/search")
async def search_tickets(query: SearchQuery):
    return get_tickets_from_web(query.departure.lower(), query.arrival.lower(), query.date)




@app.get("/my-tickets/{user_id}")
async def get_user_tickets(user_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Выбираем все колонки из таблицы tickets для данного пользователя
        rows = await conn.fetch(
            "SELECT destination, departure_date, train_number, carriage_type, price FROM tickets WHERE user_id = $1 ORDER BY departure_date DESC",
            user_id
        )
        # Преобразуем данные в список словарей для отправки в JS
        tickets = []
        for row in rows:
            ticket = dict(row)
            # Форматируем дату в строку, чтобы JS было проще её читать
            ticket['departure_date'] = ticket['departure_date'].strftime('%Y-%m-%d')
            # Преобразуем Decimal в float для JSON
            ticket['price'] = float(ticket['price'])
            tickets.append(ticket)
            
        return tickets
    except Exception as e:
        print(f"Ошибка получения билетов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера при получении билетов")
    finally:
        await conn.close()



@app.post("/send-ticket")
async def send_ticket_endpoint(data: BookingData):
    # 1. Сначала отправляем письмо
    email_sent = send_email(data)
    
    # 2. Сохраняем в базу
    if data.user_id:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            # ПРЕОБРАЗОВАНИЕ: превращаем строку '2026-01-17' в объект даты
            # Если поле уже является объектом date (благодаря Pydantic), 
            # этот код всё равно отработает корректно.
            valid_date = datetime.strptime(str(data.departure_date), "%Y-%m-%d").date()

            await conn.execute(
                """INSERT INTO tickets (user_id, destination, departure_date, train_number, carriage_type, price)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                data.user_id, 
                data.destination, 
                valid_date,  # Используем преобразованную дату
                data.train_number, 
                data.carriage_type, 
                data.price
            )
        except Exception as e:
            print(f"Ошибка БД: {e}")
        finally:
            await conn.close()

    if email_sent: 
        return {"status": "success"}
    
    raise HTTPException(status_code=500, detail="Ошибка отправки")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)