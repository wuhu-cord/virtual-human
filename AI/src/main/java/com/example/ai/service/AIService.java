package com.example.ai.service;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import lombok.extern.slf4j.Slf4j;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

@Slf4j
@Service
public class AIService {

    @Value("${ai.token}")
    private String AI_TOKEN;
    @Value("${ai.api.url}")
    private String AI_API_URL;
    @Value("${tts.api.url}")
    private String TTS_API_URL;
    @Value("${duix.submit.url}")
    private String DUIX_SUBMIT_URL;
    @Value("${duix.query.url}")
    private String DUIX_QUERY_URL;
    @Value("${avatar.video.id}")
    private String AVATAR_VIDEO_ID;
    @Value("${reference.audio.path}")
    private String REFERENCE_AUDIO_PATH;
    @Value("${reference.text}")
    private String REFERENCE_TEXT;
    @Value("${file.base.dir}")
    private String BASE_DIR;
    @Value("${file.temp.dir}")
    private String TEMP_DIR;
    @Value("${file.result.dir}")
    private String RESULT_DIR;

    // ====================== AI对话 ======================
    public String aiChat(String question) {
        log.info("【AI对话】用户问题：{}", question);
        try (CloseableHttpClient httpClient = HttpClients.createDefault()) {
            HttpPost httpPost = new HttpPost(AI_API_URL);
            httpPost.setHeader("Content-Type", "application/json");
            httpPost.setHeader("Authorization", "Bearer " + AI_TOKEN);

            JSONObject requestBody = new JSONObject();
            requestBody.put("model", "gpt-3.5-turbo");
            requestBody.put("temperature", 0.7);
            requestBody.put("stream", false);
            requestBody.put("max_tokens", 500);

            JSONArray messages = new JSONArray();
            JSONObject systemPrompt = new JSONObject();
            systemPrompt.put("role", "system");
            systemPrompt.put("content", "你是一个友好的助手，回答问题请使用完整的长句，至少说2句话，不要使用短句。");
            messages.add(systemPrompt);

            JSONObject userPrompt = new JSONObject();
            userPrompt.put("role", "user");
            userPrompt.put("content", question);
            messages.add(userPrompt);
            requestBody.put("messages", messages);

            httpPost.setEntity(new StringEntity(requestBody.toJSONString(), StandardCharsets.UTF_8));

            for (int retry = 0; retry < 3; retry++) {
                try (CloseableHttpResponse response = httpClient.execute(httpPost)) {
                    if (response.getStatusLine().getStatusCode() == 200) {
                        String result = EntityUtils.toString(response.getEntity(), StandardCharsets.UTF_8);
                        JSONObject aiResult = JSON.parseObject(result);
                        String reply = aiResult.getJSONArray("choices")
                                .getJSONObject(0)
                                .getJSONObject("message")
                                .getString("content");
                        log.info("【AI对话】返回结果：{}", reply);
                        return reply;
                    }
                } catch (Exception e) {
                    log.warn("【AI对话】第{}次重试失败", retry+1);
                    Thread.sleep(2000);
                }
            }
            return "【AI 服务异常】网络连接失败，请检查密钥、网络";
        } catch (Exception e) {
            log.error("【AI对话】异常", e);
            return "【AI 服务异常】" + e.getMessage().substring(0, 80);
        }
    }

    // ====================== ✅ 修复完成：TTS 语音生成 ======================
    // ====================== ✅ 修复：TTS 语音生成（真正能用的版本） ======================
    public String textToAudio(String text) {
        log.info("【TTS】开始生成语音，文本：{}", text);
        String tempDirPath = BASE_DIR + File.separator + TEMP_DIR;
        File tempDir = new File(tempDirPath);
        if (!tempDir.exists()) tempDir.mkdirs();

        try (CloseableHttpClient httpClient = HttpClients.createDefault()) {
            // ✅ 正确地址：你原来配置的 v1/invoke，这才是你本地真实的 TTS 接口
            HttpPost httpPost = new HttpPost("http://127.0.0.1:18180/v1/invoke");
            httpPost.setHeader("Content-Type", "application/json");

            JSONObject requestBody = new JSONObject();
            requestBody.put("text", text);
            requestBody.put("chunk_length", 100);
            requestBody.put("format", "wav");
            requestBody.put("reference_text", REFERENCE_TEXT);
            requestBody.put("reference_audio", REFERENCE_AUDIO_PATH);
            requestBody.put("references", new JSONArray());
            requestBody.put("language", "zh"); // 关键：加语言，否则报错
            requestBody.put("streaming", false);

            httpPost.setEntity(new StringEntity(requestBody.toJSONString(), StandardCharsets.UTF_8));

            try (CloseableHttpResponse response = httpClient.execute(httpPost)) {
                int statusCode = response.getStatusLine().getStatusCode();
                log.info("【TTS】返回状态码：{}", statusCode);

                if (statusCode != 200) {
                    log.error("【TTS】请求失败，返回内容：{}", EntityUtils.toString(response.getEntity()));
                    return null;
                }

                // 保存音频
                String audioFilename = UUID.randomUUID().toString().replace("-", "") + ".wav";
                String audioFullPath = tempDirPath + File.separator + audioFilename;

                try (FileOutputStream fos = new FileOutputStream(audioFullPath)) {
                    fos.write(EntityUtils.toByteArray(response.getEntity()));
                }

                File audioFile = new File(audioFullPath);
                if (audioFile.length() < 1024) {
                    log.error("【TTS】音频文件无效");
                    return null;
                }

                log.info("【TTS】音频生成成功：{}", audioFullPath);
                return audioFilename;
            }
        } catch (Exception e) {
            log.error("【TTS】生成异常", e);
            return null;
        }
    }

    // ====================== 数字人视频生成 ======================
    public String generateAvatarVideo(String audioFilename) {
        log.info("【视频合成】开始生成，音频文件：{}", audioFilename);
        String taskCode = UUID.randomUUID().toString().replace("-", "");

        try (CloseableHttpClient httpClient = HttpClients.createDefault()) {
            HttpPost submitPost = new HttpPost(DUIX_SUBMIT_URL);
            submitPost.setHeader("Content-Type", "application/json");
            JSONObject submitBody = new JSONObject();
            submitBody.put("audio_url", audioFilename);
            submitBody.put("video_url", AVATAR_VIDEO_ID);
            submitBody.put("code", taskCode);
            submitBody.put("chaofen", 0);
            submitBody.put("watermark_switch", 0);
            submitBody.put("pn", 1);
            submitPost.setEntity(new StringEntity(submitBody.toJSONString(), StandardCharsets.UTF_8));

            try (CloseableHttpResponse submitResp = httpClient.execute(submitPost)) {
                if (submitResp.getStatusLine().getStatusCode() != 200) {
                    log.error("【视频合成】任务提交失败");
                    return null;
                }
            }

            for (int i = 0; i < 60; i++) {
                try {
                    HttpGet queryGet = new HttpGet(DUIX_QUERY_URL + "?code=" + taskCode);
                    try (CloseableHttpResponse queryResp = httpClient.execute(queryGet)) {
                        String result = EntityUtils.toString(queryResp.getEntity(), StandardCharsets.UTF_8);
                        JSONObject queryResult = JSON.parseObject(result);
                        log.info("【视频合成】进度：{}", queryResult);

                        JSONObject data = queryResult.getJSONObject("data");
                        if (data == null) {
                            Thread.sleep(3000);
                            continue;
                        }

                        Integer status = data.getInteger("status");
                        if (status == 2) {
                            String videoRelativePath = data.getString("result");
                            if (videoRelativePath == null) return null;
                            String videoFilename = new File(videoRelativePath).getName();

                            String videoFullPath = BASE_DIR + File.separator + TEMP_DIR + File.separator + videoFilename;
                            File videoFile = new File(videoFullPath);

                            if (!videoFile.exists()) {
                                videoFullPath = BASE_DIR + File.separator + RESULT_DIR + File.separator + videoFilename;
                                videoFile = new File(videoFullPath);
                            }

                            if (videoFile.exists() && videoFile.length() > 1024) {
                                log.info("【视频合成】生成成功：{}", videoFullPath);
                                return videoFullPath;
                            }
                        } else if (status == 3) {
                            log.error("【视频合成】任务失败");
                            return null;
                        }
                    }
                    Thread.sleep(3000);
                } catch (Exception e) {
                    Thread.sleep(3000);
                }
            }
            return null;
        } catch (Exception e) {
            log.error("【视频合成】异常", e);
            return null;
        }
    }

    // 视频路径转换
    public String getVideoAccessUrl(String localPath) {
        String basePath = BASE_DIR.replace("\\", "/");
        String relativePath = localPath.replace("\\", "/").replace(basePath, "");
        return "/video" + relativePath;
    }
}