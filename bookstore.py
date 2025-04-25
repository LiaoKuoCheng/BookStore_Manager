import sqlite3
from typing import Optional, Tuple, List, Dict, Any

DB_NAME = "bookstore.db"

def connect_db() -> sqlite3.Connection:

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    return conn

def validate_date(date_str: str) -> bool:

    if len(date_str) != 10 or date_str.count('-') != 2:
        return False
    try:
        year, month, day = map(int, date_str.split('-'))
        if month < 1 or month > 12 or day < 1 or day > 31:
            return False
    except ValueError:
        return False
    return True

def get_member_name(conn: sqlite3.Connection, mid: str) -> Optional[str]:

    cursor = conn.cursor()
    cursor.execute("SELECT mname FROM member WHERE mid = ?", (mid,))
    row = cursor.fetchone()
    return row['mname'] if row else None

def get_book_info(conn: sqlite3.Connection, bid: str) -> Optional[Dict[str, Any]]:
 
    cursor = conn.cursor()
    cursor.execute("SELECT btitle, bprice, bstock FROM book WHERE bid = ?", (bid))
    row = cursor.fetchone()
    if row:
        return {
            'btitle': row['btitle'],
            'bprice': row['bprice'],
            'bstock': row['bstock']
        }
    return None

def add_sale(conn: sqlite3.Connection) -> None:
    try:
        # 獲取輸入
        sdate = input("請輸入銷售日期 (YYYY-MM-DD)：")
        if not validate_date(sdate):
            print("=> 錯誤：日期格式無效，請使用 YYYY-MM-DD 格式")
            return

        mid = input("請輸入會員編號：")
        if not get_member_name(conn, mid):
            print("=> 錯誤：會員編號不存在")
            return

        bid = input("請輸入書籍編號：")
        book_info = get_book_info(conn, bid)
        if not book_info:
            print("=> 錯誤：書籍編號不存在")
            return

        # 獲取數量並驗證
        try:
            sqty = int(input("請輸入購買數量："))
            if sqty <= 0:
                print("=> 錯誤：數量必須為正整數")
                return
        except ValueError:
            print("=> 錯誤：數量必須為整數")
            return

        # 檢查庫存
        if book_info['bstock'] < sqty:
            print(f"=> 錯誤：書籍庫存不足 (現有庫存: {book_info['bstock']})")
            return

        # 獲取折扣並驗證
        try:
            sdiscount = int(input("請輸入折扣金額："))
            if sdiscount < 0:
                print("=> 錯誤：折扣金額不能為負數")
                return
        except ValueError:
            print("=> 錯誤：折扣金額必須為整數")
            return

        # 計算總額
        stotal = (book_info['bprice'] * sqty) - sdiscount

        # 開始事務
        conn.execute("BEGIN TRANSACTION")
        
        # 新增銷售記錄
        conn.execute(
            "INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES (?, ?, ?, ?, ?, ?)",
            (sdate, mid, bid, sqty, sdiscount, stotal)
        )
        
        # 更新庫存
        conn.execute(
            "UPDATE book SET bstock = bstock - ? WHERE bid = ?",
            (sqty, bid)
        )
        
        # 提交事務
        conn.commit()
        
        print(f"=> 銷售記錄已新增！(銷售總額: {stotal:,})")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"=> 資料庫錯誤：{e}")
    except Exception as e:
        conn.rollback()
        print(f"=> 發生錯誤：{e}")

def print_sale_report(conn: sqlite3.Connection) -> None:
    """顯示銷售報表"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.sid, s.sdate, m.mname, b.btitle, b.bprice, 
                   s.sqty, s.sdiscount, s.stotal
            FROM sale s
            JOIN member m ON s.mid = m.mid
            JOIN book b ON s.bid = b.bid
            ORDER BY s.sid
        """)
        sales = cursor.fetchall()
        
        if not sales:
            print("=> 目前沒有銷售記錄")
            return
        
        for sale in sales:
            print("\n==================== 銷售報表 ====================")
            print(f"銷售 #{sale['sid']}")
            print(f"銷售編號: {sale['sid']}")
            print(f"銷售日期: {sale['sdate']}")
            print(f"會員姓名: {sale['mname']}")
            print(f"書籍標題: {sale['btitle']}")
            print("--------------------------------------------------")
            print("單價\t數量\t折扣\t小計")
            print("--------------------------------------------------")
            print(f"{sale['bprice']:,}\t{sale['sqty']}\t{sale['sdiscount']:,}\t{sale['stotal']:,}")
            print("--------------------------------------------------")
            print(f"銷售總額: {sale['stotal']:,}")
            print("==================================================")
            
    except sqlite3.Error as e:
        print(f"=> 資料庫錯誤：{e}")

def list_sales(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """列出所有銷售記錄
    
    Returns:
        List[Dict[str, Any]]: 銷售記錄列表
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.sid, s.sdate, m.mname
            FROM sale s
            JOIN member m ON s.mid = m.mid
            ORDER BY s.sid
        """)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"=> 資料庫錯誤：{e}")
        return []

def update_sale(conn: sqlite3.Connection) -> None:
    """更新銷售記錄"""
    sales = list_sales(conn)
    if not sales:
        print("=> 目前沒有可更新的銷售記錄")
        return
    
    print("\n======== 銷售記錄列表 ========")
    for i, sale in enumerate(sales, 1):
        print(f"{i}. 銷售編號: {sale['sid']} - 會員: {sale['mname']} - 日期: {sale['sdate']}")
    print("================================")
    
    choice = input("請選擇要更新的銷售編號 (輸入數字或按 Enter 取消): ")
    if not choice:
        return
    
    try:
        choice = int(choice)
        if choice < 1 or choice > len(sales):
            print("=> 錯誤：請輸入有效的數字")
            return
        
        sid = sales[choice-1]['sid']
        
        # 獲取新的折扣金額
        try:
            new_discount = int(input("請輸入新的折扣金額："))
            if new_discount < 0:
                print("=> 錯誤：折扣金額不能為負數")
                return
        except ValueError:
            print("=> 錯誤：折扣金額必須為整數")
            return
        
        # 開始事務
        conn.execute("BEGIN TRANSACTION")
        
        # 獲取原始銷售記錄
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.sqty, b.bprice
            FROM sale s
            JOIN book b ON s.bid = b.bid
            WHERE s.sid = ?
        """, (sid,))
        sale_info = cursor.fetchone()
        
        if not sale_info:
            print("=> 錯誤：找不到指定的銷售記錄")
            conn.rollback()
            return

        new_total = (sale_info['bprice'] * sale_info['sqty']) - new_discount
        
        conn.execute("""
            UPDATE sale 
            SET sdiscount = ?, stotal = ?
            WHERE sid = ?
        """, (new_discount, new_total, sid))
        
        conn.commit()
        
        print(f"=> 銷售編號 {sid} 已更新！(銷售總額: {new_total:,})")
        
    except ValueError:
        print("=> 錯誤：請輸入有效的數字")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"=> 資料庫錯誤：{e}")

def delete_sale(conn: sqlite3.Connection) -> None:
    
    sales = list_sales(conn)
    if not sales:
        print("=> 目前沒有可刪除的銷售記錄")
        return
    
    print("\n======== 銷售記錄列表 ========")
    for i, sale in enumerate(sales, 1):
        print(f"{i}. 銷售編號: {sale['sid']} - 會員: {sale['mname']} - 日期: {sale['sdate']}")
    print("================================")
    
    choice = input("請選擇要刪除的銷售編號 (輸入數字或按 Enter 取消): ")
    if not choice:
        return
    
    try:
        choice = int(choice)
        if choice < 1 or choice > len(sales):
            print("=> 錯誤：請輸入有效的數字")
            return
        
        sid = sales[choice-1]['sid']
        
        # 確認刪除
        confirm = input(f"確定要刪除銷售編號 {sid} 嗎？(y/n): ")
        if confirm.lower() != 'y':
            print("=> 取消刪除操作")
            return
        
        # 開始事務
        conn.execute("BEGIN TRANSACTION")
        
        # 獲取銷售記錄以恢復庫存
        cursor = conn.cursor()
        cursor.execute("""
            SELECT bid, sqty FROM sale WHERE sid = ?
        """, (sid,))
        sale_info = cursor.fetchone()
        
        if sale_info:
            # 恢復庫存
            conn.execute("""
                UPDATE book 
                SET bstock = bstock + ? 
                WHERE bid = ?
            """, (sale_info['sqty'], sale_info['bid']))
            
            # 刪除銷售記錄
            conn.execute("""
                DELETE FROM sale WHERE sid = ?
            """, (sid,))
        
        # 提交事務
        conn.commit()
        
        print(f"=> 銷售編號 {sid} 已刪除")
        
    except ValueError:
        print("=> 錯誤：請輸入有效的數字")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"=> 資料庫錯誤：{e}")

def main() -> None:
    """主程式"""
    try:
        with connect_db() as conn:
            while True:
                print("\n***************選單***************")
                print("1. 新增銷售記錄")
                print("2. 顯示銷售報表")
                print("3. 更新銷售記錄")
                print("4. 刪除銷售記錄")
                print("5. 離開")
                print("**********************************")
                
                choice = input("請選擇操作項目(Enter 離開)：").strip()
                
                if not choice:
                    break
                if choice == '1':
                    add_sale(conn)
                elif choice == '2':
                    print_sale_report(conn)
                elif choice == '3':
                    update_sale(conn)
                elif choice == '4':
                    delete_sale(conn)
                elif choice == '5':
                    break
                else:
                    print("=> 請輸入有效的選項（1-5）")
    except sqlite3.Error as e:
        print(f"=> 資料庫連接錯誤：{e}")
    except Exception as e:
        print(f"=> 發生錯誤：{e}")
    finally:
        print("\n=> 程式結束")

if __name__ == "__main__":
    main()