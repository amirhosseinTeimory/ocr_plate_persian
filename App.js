import React, { useState, useEffect } from 'react';
import { View, Button, Text, StyleSheet, Image, ScrollView, ActivityIndicator, Alert } from 'react-native';
import io from 'socket.io-client';

const App = () => {
  const [ledState, setLedState] = useState(false); // وضعیت LED
  const [plateText, setPlateText] = useState("متن پلاک دریافت نشده است"); // متن پلاک
  const [imageUrl, setImageUrl] = useState(null); // URL تصویر پلاک
  const [loading, setLoading] = useState(false); // وضعیت بارگذاری

  // اتصال به WebSocket
  useEffect(() => {
    const socket = io("http://192.168.135.49:5000"); // آدرس سرور WebSocket

    socket.on('connect', () => {
      console.log("🟢 WebSocket Connected");
    });

    // دریافت اطلاعات پلاک از سرور
    socket.on('new_plate', (data) => {
      console.log("🟢 Plate Data Received (JSON):", data);
      setPlateText(data.plate_text || "پلاک تشخیص داده نشد");
      setImageUrl(data.image_url || null);
    });


    socket.on('disconnect', () => {
      console.log("🔴 WebSocket Disconnected");
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  // توابع مربوط به روشن و خاموش کردن LED
  const toggleLed = async () => {
    try {
      setLoading(true); // نمایش وضعیت بارگذاری 
      //http://192.168.1.101:5000/toggle_led
      const response = await fetch('http://192.168.135.49:5000/toggle_led', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: ledState ? 'off' : 'on' }),
      });
      const data = await response.json(); // دریافت پاسخ
      console.log("Toggle LED Response:", data);
      if (response.ok) {
        setLedState(!ledState);
      } else {
        Alert.alert("خطا", "خطا در تغییر وضعیت LED");
      }
    } catch (error) {
      console.error("Server Connection Error:", error);
      Alert.alert("خطا", "خطا در اتصال به سرور");
    } finally {
      setLoading(false); // پایان بارگذاری
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {/* دکمه کنترل LED */}
      <Button
        title={ledState ? "خاموش کردن LED" : "روشن کردن LED"}
        onPress={toggleLed}
        disabled={loading} // غیرفعال کردن دکمه هنگام بارگذاری
      />

      {loading && <ActivityIndicator size="small" color="#0000ff" style={styles.spinner} />}

      {/* نمایش متن پلاک */}
      <Text style={styles.text}>متن پلاک: {plateText}</Text>

      {/* نمایش تصویر پلاک */}
      {imageUrl ? (
        <Image
          source={{ uri: imageUrl }}
          style={styles.image}
        />
      ) : (
        <Text style={styles.text}>تصویری برای نمایش وجود ندارد</Text>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20, backgroundColor: '#f9f9f9' },
  spinner: { marginVertical: 10 },
  text: { marginTop: 20, fontSize: 18, textAlign: 'center', color: '#333' },
  image: { marginTop: 20, width: 300, height: 150, resizeMode: 'contain', borderWidth: 1, borderColor: 'gray' },
});

export default App;
