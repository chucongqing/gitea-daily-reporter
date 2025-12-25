# 1. 使用官方镜像
FROM python:3.9-slim

WORKDIR /app

# 2. 【关键】先只将 requirements.txt 拷贝到镜像中
COPY requirements.txt .

# 3. 安装依赖
# 只要 requirements.txt 没变，Docker 就会跳过这一步，直接使用缓存
RUN pip install --proxy http://192.168.3.80:38201 --no-cache-dir -r requirements.txt

# 4. 最后再拷贝剩下的源代码
# 即使代码变了，也不会影响上面已经安装好的依赖层
COPY . .

EXPOSE 5000
ENV WEB_PORT=5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
