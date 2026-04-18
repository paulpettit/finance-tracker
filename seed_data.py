import sqlite3
conn = sqlite3.connect('finance.db')

rows = [
    # Feb 2024 - car repair, tight month (net ~+200)
    (1,'2024-02-01','Salary Deposit',3250.00,'Income'),
    (1,'2024-02-04','Whole Foods',-138.40,'Groceries'),
    (1,'2024-02-07','Netflix',-15.99,'Entertainment'),
    (1,'2024-02-09','Auto Repair',-820.00,'Transport'),
    (1,'2024-02-14','Uber',-22.50,'Transport'),
    (1,'2024-02-18','Amazon',-54.20,'Shopping'),
    (1,'2024-02-20','Rent',-1500.00,'Housing'),
    (1,'2024-02-25','CVS Pharmacy',-38.10,'Health'),
    (1,'2024-02-27','Starbucks',-17.80,'Food & Drink'),
    (1,'2024-02-28','Shell Gas',-60.00,'Transport'),
    # Mar 2024 - normal month (net ~+900)
    (1,'2024-03-01','Salary Deposit',3250.00,'Income'),
    (1,'2024-03-03','Whole Foods',-121.60,'Groceries'),
    (1,'2024-03-06','Spotify',-9.99,'Entertainment'),
    (1,'2024-03-10','DoorDash',-36.40,'Food & Drink'),
    (1,'2024-03-14','Shell Gas',-58.30,'Transport'),
    (1,'2024-03-18','Rent',-1500.00,'Housing'),
    (1,'2024-03-22','Target',-87.50,'Shopping'),
    (1,'2024-03-28','Gym Membership',-45.00,'Gym'),
    (1,'2024-03-30','Electric Bill',-94.20,'Utilities'),
    # Apr 2024 - vacation (net -300)
    (1,'2024-04-01','Salary Deposit',3250.00,'Income'),
    (1,'2024-04-03','Whole Foods',-112.80,'Groceries'),
    (1,'2024-04-05','Airbnb',-680.00,'Travel'),
    (1,'2024-04-07','Netflix',-15.99,'Entertainment'),
    (1,'2024-04-10','Delta Airlines',-540.00,'Travel'),
    (1,'2024-04-15','Rent',-1500.00,'Housing'),
    (1,'2024-04-18','Restaurants',-210.40,'Food & Drink'),
    (1,'2024-04-22','Uber',-48.60,'Transport'),
    (1,'2024-04-28','Amazon',-95.30,'Shopping'),
    # May 2024 - freelance bonus (net ~+2100)
    (1,'2024-05-01','Salary Deposit',3250.00,'Income'),
    (1,'2024-05-02','Freelance Payment',1200.00,'Income'),
    (1,'2024-05-05','Whole Foods',-129.90,'Groceries'),
    (1,'2024-05-09','Spotify',-9.99,'Entertainment'),
    (1,'2024-05-12','DoorDash',-41.20,'Food & Drink'),
    (1,'2024-05-16','Shell Gas',-64.70,'Transport'),
    (1,'2024-05-20','Rent',-1500.00,'Housing'),
    (1,'2024-05-24','Target',-73.40,'Shopping'),
    (1,'2024-05-29','Electric Bill',-88.50,'Utilities'),
    # Jun 2024 - dental + rent hike (net ~+400)
    (1,'2024-06-01','Salary Deposit',3250.00,'Income'),
    (1,'2024-06-03','Whole Foods',-144.10,'Groceries'),
    (1,'2024-06-06','Netflix',-15.99,'Entertainment'),
    (1,'2024-06-09','Dentist',-420.00,'Health'),
    (1,'2024-06-12','Uber',-28.30,'Transport'),
    (1,'2024-06-15','Rent',-1600.00,'Housing'),
    (1,'2024-06-19','Amazon',-102.50,'Shopping'),
    (1,'2024-06-24','DoorDash',-55.80,'Food & Drink'),
    (1,'2024-06-28','Gym Membership',-45.00,'Gym'),
    # Jul 2024 - slow work month (net -150)
    (1,'2024-07-01','Salary Deposit',2100.00,'Income'),
    (1,'2024-07-04','BBQ Groceries',-88.40,'Food & Drink'),
    (1,'2024-07-08','Whole Foods',-136.20,'Groceries'),
    (1,'2024-07-11','Spotify',-9.99,'Entertainment'),
    (1,'2024-07-15','Rent',-1600.00,'Housing'),
    (1,'2024-07-18','Shell Gas',-71.30,'Transport'),
    (1,'2024-07-22','Target',-94.60,'Shopping'),
    (1,'2024-07-27','Electric Bill',-112.40,'Utilities'),
    (1,'2024-07-30','DoorDash',-48.70,'Food & Drink'),
    # Aug 2024 - back to normal + side gig (net ~+1800)
    (1,'2024-08-01','Salary Deposit',3250.00,'Income'),
    (1,'2024-08-03','Side Gig',550.00,'Income'),
    (1,'2024-08-05','Whole Foods',-118.30,'Groceries'),
    (1,'2024-08-08','Netflix',-15.99,'Entertainment'),
    (1,'2024-08-12','Uber',-19.40,'Transport'),
    (1,'2024-08-15','Rent',-1600.00,'Housing'),
    (1,'2024-08-20','Amazon',-78.90,'Shopping'),
    (1,'2024-08-25','Gym Membership',-45.00,'Gym'),
    (1,'2024-08-29','Electric Bill',-98.60,'Utilities'),
    # Sep 2024 - normal (net ~+900)
    (1,'2024-09-02','Salary Deposit',3250.00,'Income'),
    (1,'2024-09-04','Whole Foods',-126.40,'Groceries'),
    (1,'2024-09-07','Spotify',-9.99,'Entertainment'),
    (1,'2024-09-10','DoorDash',-44.20,'Food & Drink'),
    (1,'2024-09-14','Shell Gas',-62.80,'Transport'),
    (1,'2024-09-18','Rent',-1600.00,'Housing'),
    (1,'2024-09-22','Target',-81.30,'Shopping'),
    (1,'2024-09-27','Gym Membership',-45.00,'Gym'),
    (1,'2024-09-30','Electric Bill',-86.70,'Utilities'),
    # Oct 2024 - medical emergency (net -400)
    (1,'2024-10-01','Salary Deposit',3250.00,'Income'),
    (1,'2024-10-03','Whole Foods',-133.60,'Groceries'),
    (1,'2024-10-06','Netflix',-15.99,'Entertainment'),
    (1,'2024-10-08','ER Visit',-950.00,'Health'),
    (1,'2024-10-12','Pharmacy',-180.40,'Health'),
    (1,'2024-10-15','Rent',-1600.00,'Housing'),
    (1,'2024-10-19','Amazon',-67.20,'Shopping'),
    (1,'2024-10-24','Uber',-33.10,'Transport'),
    (1,'2024-10-29','Electric Bill',-104.30,'Utilities'),
    # Nov 2024 - holiday shopping (net ~+200)
    (1,'2024-11-01','Salary Deposit',3250.00,'Income'),
    (1,'2024-11-04','Whole Foods',-158.90,'Groceries'),
    (1,'2024-11-07','Spotify',-9.99,'Entertainment'),
    (1,'2024-11-11','Amazon',-342.50,'Shopping'),
    (1,'2024-11-15','Rent',-1600.00,'Housing'),
    (1,'2024-11-19','Target',-188.60,'Shopping'),
    (1,'2024-11-22','DoorDash',-62.40,'Food & Drink'),
    (1,'2024-11-27','Shell Gas',-58.90,'Transport'),
    (1,'2024-11-29','Electric Bill',-92.40,'Utilities'),
    # Dec 2024 - holidays + travel (net -600)
    (1,'2024-12-01','Salary Deposit',3250.00,'Income'),
    (1,'2024-12-03','Whole Foods',-162.30,'Groceries'),
    (1,'2024-12-05','Delta Airlines',-480.00,'Travel'),
    (1,'2024-12-08','Netflix',-15.99,'Entertainment'),
    (1,'2024-12-12','Gift Shopping',-520.00,'Shopping'),
    (1,'2024-12-15','Rent',-1600.00,'Housing'),
    (1,'2024-12-18','Restaurants',-188.50,'Food & Drink'),
    (1,'2024-12-22','Amazon',-134.70,'Shopping'),
    (1,'2024-12-27','Electric Bill',-118.20,'Utilities'),
    (1,'2024-12-30','Uber',-42.60,'Transport'),
]

conn.executemany(
    'INSERT INTO transactions (account_id, date, description, amount, category) VALUES (?, ?, ?, ?, ?)',
    rows
)
conn.commit()
total = conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
months = conn.execute("SELECT DISTINCT substr(date,1,7) FROM transactions ORDER BY 1").fetchall()
print('Total:', total, '| Months:', [m[0] for m in months])
conn.close()
