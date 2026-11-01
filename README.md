# התראות משרות סטודנט

סורק את עמודי הגיוס של NVIDIA, Intel, Applied Materials, Apple ו-Microsoft בישראל כל 10 דקות.
כשעולה משרת סטודנט או ג'וניור שמתאימה לחומרה/ולידציה, נשלחת הודעה בטלגרם עם קישור להגשה.
**המערכת לא מגישה מועמדות אף פעם.** היא רק קוראת רשימות משרות ציבוריות.

## איך זה עובד
- רץ ב-GitHub Actions, בענן, בלי תלות במחשב. `watch.yml` מריץ 5 סריקות נפרדות במקביל, אחת לכל חברה.
- לכל חברה יש סורק משלו ב-`jobwatch/sources/`, כי כל אתר בנוי אחרת. ההסבר על כל אתר כתוב בראש הקובץ שלו.
- משרה חדשה עוברת סינון: ישראל → סטודנט/ג'וניור → תחום (`config.yaml`) → ציון התאמה מ-Claude מול תקציר המועמדת.
- סיכום יומי ב-20:00 עם כל המשרות המתאימות שעדיין פתוחות. הוא משמש גם כסימן שהמערכת חיה.
- אם אתר נכשל 3 פעמים ברצף (למשל כי שינה מבנה), נשלחת התראת תקלה.

## הקמה (פעם אחת)
1. **בוט טלגרם**: בטלגרם פותחים צ'אט עם `@BotFather`, שולחים `/newbot` ושומרים את הטוקן.
2. **קבוצה**: יוצרים קבוצה, מוסיפים אליה את מי שצריך לקבל התראות ואת הבוט, וכותבים בה הודעה כלשהי.
   ה-chat id נמצא בכתובת `https://api.telegram.org/bot<TOKEN>/getUpdates`, בשדה `"chat":{"id":-100...}`.
3. **מפתח Claude** (לא חובה, אבל מסנן רעש): ב-console.anthropic.com יוצרים API key ומגדירים תקרת הוצאה חודשית.
4. **GitHub**: יוצרים repo **ציבורי** (ב-repo ציבורי דקות הריצה ללא הגבלה) ודוחפים אליו את התיקייה.
5. ב-repo נכנסים ל-Settings → Secrets and variables → Actions ומוסיפים:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID` (אפשר כמה, מופרדים בפסיק)
   - `ANTHROPIC_API_KEY`
   - `PROFILE_TEXT`: תקציר מקצועי של המועמדת בשביל ה-AI. נשמר מוצפן ולא מופיע ב-repo.
   - `TELEGRAM_ADMIN_CHAT_ID`, לא חובה: לאן לשלוח התראות תקלה. אם ריק, הן נשלחות לקבוצה.
6. בלשונית Actions מפעילים את ה-workflows ומריצים ידנית את `watch` (Run workflow).
   בהרצה הראשונה כל חברה שולחת הודעת פתיחה עם המשרות המתאימות שכבר פתוחות.

## שינויים נפוצים
- **מילות מפתח, ספים, הוספה או הסרה של חברה מהסריקה**: `config.yaml`.
- **מה ה-AI יודע על המועמדת**: ה-Secret `PROFILE_TEXT`. מקומית הוא נקרא מ-`profile.md`, שלא נכנס ל-git. לעדכון: `gh secret set PROFILE_TEXT < profile.md`.
- **להוסיף חברה חדשה**: כותבים מודול ב-`jobwatch/sources/` עם `NAME`, `DISPLAY`, `fetch_jobs` ו-`fetch_description`, רושמים אותו ב-`sources/__init__.py` ומוסיפים אותו ל-matrix ב-`watch.yml`.

## הרצה מקומית
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m jobwatch --dry-run                    # מה מתאים עכשיו, בלי לשלוח
.venv/bin/python -m jobwatch --company apple --dry-run    # חברה אחת
.venv/bin/python -m pytest                                # בדיקות
```
