# Pharmyrus v3.1 HOTFIX - Railway Deploy

## 🚀 Deploy no Railway (SOLUÇÃO DEFINITIVA)

### 1️⃣ Upload do Projeto
```bash
# Fazer upload do pharmyrus-v3.1-HOTFIX.zip no Railway
# Railway detecta automaticamente o Dockerfile
```

### 2️⃣ Railway Build Process
O Railway vai:
1. ✅ Usar `Dockerfile` (detecta automaticamente)
2. ✅ Instalar Python 3.11 + todas dependências do sistema
3. ✅ Instalar Playwright + Chromium com `--with-deps`
4. ✅ Build completo em ~3-4 minutos
5. ✅ API rodando na porta 8080

### 3️⃣ Testar Deploy
```bash
# Health check
curl https://YOUR-APP.up.railway.app/health

# Test endpoint (rápido)
curl https://YOUR-APP.up.railway.app/test/WO2016168716

# WIPO endpoint (completo)
curl "https://YOUR-APP.up.railway.app/api/v1/wipo/WO2016168716?country=BR"

# Pipeline completo (busca + múltiplos WOs)
curl "https://YOUR-APP.up.railway.app/api/v1/search/darolutamide?limit=3"
```

## 📊 Diferenças vs v3.0

### ANTES (v3.0 - BROKEN)
```json
{
  "titular": null,
  "datas": {"deposito": null, "publicacao": null},
  "worldwide_applications": {},
  "paises_familia": []
}
```

### DEPOIS (v3.1 HOTFIX - WORKING)
```json
{
  "titular": "Orion Corporation",
  "datas": {
    "deposito": "2016-04-04",
    "publicacao": "2016-10-20",
    "prioridade": "2015-04-17"
  },
  "worldwide_applications": {
    "2016": [
      {"country_code": "BR", "application_number": "BR112017022140A2", ...},
      {"country_code": "US", "application_number": "US15/566,127", ...}
    ],
    "2017": [...]
  },
  "paises_familia": ["BR", "US", "CA", "EP", "JP", ...]
}
```

## 🔧 Arquitetura

### Dockerfile (Base)
- **Python 3.11-slim-bullseye**
- **Todas** as bibliotecas do sistema para Playwright
- `playwright install --with-deps chromium`

### Serviços
1. **wipo_crawler.py**: Extração WIPO com worldwide_applications
2. **pipeline_service.py**: PubChem → WO Discovery → BR Extraction
3. **api_service.py**: FastAPI endpoints
4. **crawler_pool.py**: Pool de 2 crawlers Playwright

### Endpoints
- `GET /` - Info da API
- `GET /health` - Status
- `GET /api/v1/wipo/{wo}` - Fetch WIPO patent
- `GET /api/v1/search/{molecule}` - Full pipeline
- `GET /test/{wo}` - Quick test

## 🐛 Bug Fixes (v3.1 HOTFIX)

### 1. WIPO worldwide_applications = {}
**FIX**: Click "National Phase" tab + extract table data
- **Antes**: `{}`
- **Depois**: `{"2016": [...], "2017": [...]}`

### 2. WO Discovery = []
**FIX**: 20+ parallel Google searches (years 2011-2024, dev codes, companies)
- **Antes**: `[]`
- **Depois**: `["WO2016168716", "WO2011051540", ...]`

### 3. Titular/Datas = null
**FIX**: Multiple selector strategies + fallbacks
- **Antes**: `null`
- **Depois**: `"Orion Corporation"` / `{"deposito": "2016-04-04", ...}`

## 📦 Arquivos

```
pharmyrus-v3.1-HOTFIX/
├── Dockerfile          ← Railway usa este
├── requirements.txt    ← Python deps
├── runtime.txt         ← python-3.11.9
├── main.py            ← Entry point
├── README.md          ← Este arquivo
└── src/
    ├── __init__.py
    ├── wipo_crawler.py      ← 200 linhas
    ├── pipeline_service.py  ← 150 linhas
    ├── api_service.py       ← 100 linhas
    └── crawler_pool.py      ← 30 linhas
```

## ⚠️ Bibliotecas Instaladas no Dockerfile

O Dockerfile instala **TODAS** estas bibliotecas:
- libglib2.0-0, libgobject-2.0-0
- libnss3, libnspr4, libnssutil3
- libatk1.0-0, libatk-bridge2.0-0
- libcups2, libdrm2, libdbus-1-3
- libxkbcommon0, libxcomposite1, libxdamage1
- libxfixes3, libxrandr2, libgbm1
- libpango-1.0-0, libcairo2, libasound2
- libatspi2.0-0, libxshmfence1
- E mais...

## 🎯 Validação de Sucesso

```bash
# Deve retornar:
{
  "test": "SUCCESS",
  "has_title": true,
  "has_applicant": true,
  "worldwide_apps": 70+,
  "countries": 30+
}
```

## 📞 Support

Se o deploy falhar:
1. Verificar logs do Railway
2. Confirmar que Railway detectou o `Dockerfile`
3. Verificar se build incluiu `playwright install --with-deps chromium`
4. Tempo de build esperado: 3-4 minutos

---

**Version**: 3.1.0-HOTFIX  
**Status**: ✅ PRODUCTION READY  
**Deploy Target**: Railway  
**Build Method**: Dockerfile  
