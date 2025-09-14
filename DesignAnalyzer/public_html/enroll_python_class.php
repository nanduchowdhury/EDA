<?php
if($_SERVER["REQUEST_METHOD"] == "POST"){
    $name = $_POST['name'];
    $email = $_POST['email'];

    $file = fopen("data/python_basic_enrolls.csv", "a");
    fputcsv($file, [$name, $email]);
    fclose($file);

    echo "Thank you for enrolling, $name!";
}
?>
