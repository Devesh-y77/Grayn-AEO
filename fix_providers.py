import glob
import re

d = 'backend/app/services/providers'
for f in glob.glob(d + '/*.py'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if 'except Exception as e:' in content and 'Falling back to mock data' in content and 'USE_MOCK_PROVIDERS' not in content:
        # We need to replace the except block to conditionally check USE_MOCK_PROVIDERS
        new_except = """        except Exception as e:
            from app.config import get_settings
            settings = get_settings()
            if settings.USE_MOCK_PROVIDERS:
                print(f"Provider exception: {e}. Falling back to mock data.")"""
        
        content = re.sub(r'\s*except Exception as e:\s*print\([^)]*Falling back to mock data[^)]*\)', new_except, content)
        
        # Now we need to append the raise e at the end of the return EngineResult
        # It's easier to just do a simple replacement for the return statement to include `raise e`
        content = content.replace("                cost_usd=0.0,\n            )", "                cost_usd=0.0,\n            )\n            raise e")
        
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print('Fixed', f)
