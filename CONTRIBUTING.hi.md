# Study Buddy में योगदान करना

आपकी रुचि के लिए धन्यवाद! यह गाइड आपको शून्य से लेकर अपने पहले PR तक 10 मिनट से भी कम समय में पहुँचाएगा।

## त्वरित सेटअप

```
git clone https://github.com/Vivek492005/STUDY-BUDDY
cd STUDY-BUDDY
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # फिर अपनी keys जोड़ें
STUDYBUDDY_NO_PARSE_SANDBOX=1 .venv/bin/python -m pytest tests/ -x -q
```

## ब्रांच और कमिट के नियम

- ब्रांच: `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>`
- कमिट: आज्ञार्थक (imperative) शैली में लिखें, और जहाँ लागू हो वहाँ task id का prefix लगाएँ — जैसे `OSS-04: add SECURITY.md`
- हर PR में एक ही तार्किक बदलाव रखें। PR छोटे और आसानी से समीक्षा-योग्य रखें।

## टेस्ट कैसे चलाएँ

```
# तेज़ (sandbox parsing के बिना)
STUDYBUDDY_NO_PARSE_SANDBOX=1 .venv/bin/python -m pytest tests/ -q

# Lint
.venv/bin/ruff check --no-cache .

# Benchmarks
.venv/bin/python benchmarks/run.py --quick
.venv/bin/python benchmarks/rag_eval.py --quick
```

## पूर्णता की परिभाषा (Definition of Done) — हर PR के लिए

- [ ] टेस्ट जोड़े/अपडेट किए गए हैं और पास हो रहे हैं (`pytest`, `ruff`)
- [ ] कोई secret commit नहीं किया गया है (push करने से पहले `git diff --cached | grep -iE 'key|token|secret'` चलाएँ)
- [ ] यदि व्यवहार (behavior) बदला है तो डॉक्स अपडेट किए गए हैं
- [ ] ईमानदारी: कोई मनगढ़ंत आँकड़े नहीं, कोई झूठे दावे नहीं

## योगदान करने के तरीके

- **कोड:** कोई `good first issue` चुनें या नया फ़ीचर सुझाएँ
- **डेटा:** skill aliases, वेतन (salary) डेटा, प्रश्न बैंक जोड़ें (देखें `scripts/validate_data.py`)
- **डॉक्स:** typos ठीक करें, गाइड बेहतर बनाएँ, अनुवाद करें
- **बेंचमार्क:** कठिन gold-set उदाहरण जोड़ें

## आचार संहिता (Code of Conduct)

दयालु और रचनात्मक बनें। देखें [CODE_OF_CONDUCT.md](https://github.com/Vivek492005/STUDY-BUDDY/blob/main/CODE_OF_CONDUCT.md).
