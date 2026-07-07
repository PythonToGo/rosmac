from setuptools import setup

package_name = "pick_demo"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    description="rosmac 예제: 맥 네이티브 rclpy 노드가 VM의 MoveIt을 액션으로 구동",
    license="MIT",
    entry_points={
        "console_scripts": [
            "pick_demo = pick_demo.pick_demo:main",
        ],
    },
)
