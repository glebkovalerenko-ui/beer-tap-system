// src/pages/GuestsPage.jsx
import { useState, useEffect } from 'react';
import { apiClient } from '../api';

export default function GuestsPage() {
  // Создаем "состояние" (state) для хранения списка гостей.
  // Изначально это пустой массив.
  const [guests, setGuests] = useState([]);

  // useEffect - это хук, который выполняется после рендера компонента.
  // Пустой массив [] в конце означает, что он выполнится только один раз,
  // когда компонент впервые появится на экране.
  useEffect(() => {
    console.log('Запрашиваем гостей с бэкенда...');
    apiClient.get('/api/guests/')
      .then(response => {
        // Если запрос успешен, обновляем состояние нашим списком гостей
        console.log('Гости успешно загружены:', response.data);
        setGuests(response.data);
      })
      .catch(error => {
        // Если произошла ошибка, выводим ее в консоль
        console.error('Ошибка загрузки гостей:', error);
      });
  }, []); // <-- Пустой массив зависимостей

  return (
    <div>
      <h2>Управление гостями</h2>
      {/* Здесь позже будет форма для создания гостя */}
      
      <h3>Список гостей</h3>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Имя</th>
            <th>Фамилия</th>
            <th>Баланс</th>
          </tr>
        </thead>
        <tbody>
          {/* Проходимся по массиву guests и для каждого гостя создаем строку в таблице */}
          {guests.map(guest => (
            <tr key={guest.guest_id}>
              <td>{guest.guest_id}</td>
              <td>{guest.first_name}</td>
              <td>{guest.last_name}</td>
              <td>{guest.balance}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}