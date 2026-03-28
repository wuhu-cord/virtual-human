package com.example.ai;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
@SpringBootApplication
public class AiApplication {
    public static void main(String[] args) {
        SpringApplication.run(AiApplication.class, args);
        System.out.println("========================================");
        System.out.println("✅ 数字人服务器启动成功！");
        System.out.println("🌐 本机访问地址：http://localhost:8080");
        System.out.println("📱 局域网访问地址：http://你的电脑IP:8080");
        System.out.println("========================================");
    }
}