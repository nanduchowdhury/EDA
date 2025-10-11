<?php
if($_SERVER["REQUEST_METHOD"] == "POST"){
    $name = $_POST['name'] ?? '';
    $whatsapp = $_POST['whatsapp'] ?? '';

    // Open CSV file in append mode
    $file = fopen("data/python_basic_enrolls.csv", "a");

    // Save name + WhatsApp number
    fputcsv($file, [$name, $whatsapp]);

    fclose($file);

    echo "Thank you for enrolling, $name! We will send you a link to the Python class on your WhatsApp number.";
}
?>
