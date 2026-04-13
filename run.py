from app import create_app

app = create_app()

if __name__ == '__main__':
    # print("启动Flask应用，访问 http://localhost:5000/test 测试基本功能")
    # print("注册的蓝图:")
    # for rule in app.url_map.iter_rules():
    #     print(f"路由: {rule}, 端点: {rule.endpoint}")
    app.run(debug=True)
