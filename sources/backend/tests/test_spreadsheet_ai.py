import pytest
from app import create_app, db
from app.config import Config
from app.models.core import User

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}
    JWT_SECRET_KEY = 'test-secret-key-12345'

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_spreadsheet_ai_endpoints(app, client):
    with app.app_context():
        user = User.query.filter_by(login_name='admin').first()
        if not user:
            user = User(login_name='admin', employee_no='ADM001', is_super_admin=True)
            user.set_password('Admin123!')
            db.session.add(user)
            db.session.commit()
        else:
            user.set_password('Admin123!')
            db.session.commit()

        login_res = client.post('/api/auth/login', json={'login_name': 'admin', 'password': 'Admin123!'})
        assert login_res.status_code == 200
        token = login_res.json['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        # 1. Test AI Formula Endpoint
        formula_res = client.post(
            '/api/ai/spreadsheet/formula',
            headers=headers,
            json={
                'query': '求第1列到第10列的总和',
                'cell_address': 'K1',
                'range_context': 'A1:J1'
            }
        )
        assert formula_res.status_code == 200
        formula_data = formula_res.json.get('data', {})
        assert 'formula' in formula_data
        assert formula_data['formula'].startswith('=')

        # 2. Test AI Table Generator Endpoint
        gen_res = client.post(
            '/api/ai/spreadsheet/generate-table',
            headers=headers,
            json={
                'prompt': '2026年Q1财务预算表',
                'row_count': 5,
                'col_count': 5
            }
        )
        assert gen_res.status_code == 200
        table_data = gen_res.json.get('data', {})
        assert 'headers' in table_data
        assert 'rows' in table_data
        assert len(table_data['headers']) > 0

        # 3. Test AI Insights Endpoint
        insights_res = client.post(
            '/api/ai/spreadsheet/insights',
            headers=headers,
            json={
                'sheet_name': '销售表',
                'headers': ['月份', '销售额', '成本'],
                'rows_sample': [['1月', 10000, 6000], ['2月', 12000, 7000]],
                'total_rows': 2
            }
        )
        assert insights_res.status_code == 200
        insights_data = insights_res.json.get('data', {})
        assert 'summary' in insights_data
        assert 'trends' in insights_data

        # 4. Test AI Process Range Endpoint
        proc_res = client.post(
            '/api/ai/spreadsheet/process-range',
            headers=headers,
            json={
                'action': 'clean',
                'range_data': [['  Apple  ', ' 100 '], [' Orange ', '200']]
            }
        )
        assert proc_res.status_code == 200
        proc_data = proc_res.json.get('data', {})
        assert 'processed_data' in proc_data
        assert len(proc_data['processed_data']) == 2
