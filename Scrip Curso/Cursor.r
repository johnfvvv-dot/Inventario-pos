if (number < 10) {

  if (number < 5) {

    result <- "extra small"

  } else {

    result <- "small"

  }

} else if (number < 100) {

  result <- "medium"

} else {

  result <- "large"

}
print(result)