from ..app.react.tools_register import tools
from ..app import create_app
app = create_app()

params = {
    "student_id": 7,
}

print(tools)
print('-'*100)
print(tools['get_student_knowledge_mastery']['function'](params))
print('-'*100)
print(tools['get_product']['function'](
    {
        "product_id": 1
    }
))

