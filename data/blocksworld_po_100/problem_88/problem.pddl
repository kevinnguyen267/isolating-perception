(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue_1 - block
		blue_10 - block
		blue_11 - block
		blue_12 - block
		blue_13 - block
		blue_14 - block
		blue_15 - block
		blue_16 - block
		blue_17 - block
		blue_2 - block
		blue_3 - block
		blue_4 - block
		blue_5 - block
		blue_6 - block
		blue_7 - block
		blue_8 - block
		blue_9 - block
		green_1 - block
		green_10 - block
		green_11 - block
		green_12 - block
		green_13 - block
		green_14 - block
		green_15 - block
		green_16 - block
		green_17 - block
		green_2 - block
		green_3 - block
		green_4 - block
		green_5 - block
		green_6 - block
		green_7 - block
		green_8 - block
		green_9 - block
		orange_1 - block
		orange_10 - block
		orange_11 - block
		orange_12 - block
		orange_13 - block
		orange_14 - block
		orange_15 - block
		orange_16 - block
		orange_17 - block
		orange_2 - block
		orange_3 - block
		orange_4 - block
		orange_5 - block
		orange_6 - block
		orange_7 - block
		orange_8 - block
		orange_9 - block
		purple_1 - block
		purple_10 - block
		purple_11 - block
		purple_12 - block
		purple_13 - block
		purple_14 - block
		purple_15 - block
		purple_16 - block
		purple_2 - block
		purple_3 - block
		purple_4 - block
		purple_5 - block
		purple_6 - block
		purple_7 - block
		purple_8 - block
		purple_9 - block
		red_1 - block
		red_10 - block
		red_11 - block
		red_12 - block
		red_13 - block
		red_14 - block
		red_15 - block
		red_16 - block
		red_2 - block
		red_3 - block
		red_4 - block
		red_5 - block
		red_6 - block
		red_7 - block
		red_8 - block
		red_9 - block
		yellow_1 - block
		yellow_10 - block
		yellow_11 - block
		yellow_12 - block
		yellow_13 - block
		yellow_14 - block
		yellow_15 - block
		yellow_16 - block
		yellow_17 - block
		yellow_2 - block
		yellow_3 - block
		yellow_4 - block
		yellow_5 - block
		yellow_6 - block
		yellow_7 - block
		yellow_8 - block
		yellow_9 - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable green_6)
		(on blue_10 green_6)
		(on yellow_11 blue_10)
		(on yellow_1 yellow_11)
		(on blue_4 yellow_1)
		(on yellow_10 blue_4)
		(on green_14 yellow_10)
		(on purple_15 green_14)
		(on orange_2 purple_15)
		(clear orange_2)

		(ontable green_15)
		(on red_10 green_15)
		(on yellow_7 red_10)
		(on purple_6 yellow_7)
		(on yellow_8 purple_6)
		(on purple_14 yellow_8)
		(on purple_13 purple_14)
		(on green_13 purple_13)
		(on purple_10 green_13)
		(clear purple_10)

		(ontable green_2)
		(on green_10 green_2)
		(on red_12 green_10)
		(on purple_16 red_12)
		(on red_9 purple_16)
		(on purple_12 red_9)
		(on orange_16 purple_12)
		(on orange_11 orange_16)
		(clear orange_11)

		(ontable orange_10)
		(on yellow_12 orange_10)
		(on red_11 yellow_12)
		(on green_9 red_11)
		(on purple_7 green_9)
		(on green_11 purple_7)
		(on yellow_9 green_11)
		(on red_5 yellow_9)
		(clear red_5)

		(ontable orange_3)
		(on blue_11 orange_3)
		(on blue_14 blue_11)
		(on purple_2 blue_14)
		(on orange_8 purple_2)
		(on yellow_16 orange_8)
		(on yellow_15 yellow_16)
		(on blue_3 yellow_15)
		(clear blue_3)

		(ontable orange_5)
		(on orange_12 orange_5)
		(on purple_3 orange_12)
		(on red_1 purple_3)
		(on purple_9 red_1)
		(on red_6 purple_9)
		(on red_16 red_6)
		(on blue_16 red_16)
		(clear blue_16)

		(ontable blue_17)
		(on green_16 blue_17)
		(on green_4 green_16)
		(on orange_13 green_4)
		(on orange_7 orange_13)
		(on red_13 orange_7)
		(on green_3 red_13)
		(on green_17 green_3)
		(clear green_17)

		(ontable red_8)
		(on orange_17 red_8)
		(on yellow_17 orange_17)
		(on blue_9 yellow_17)
		(on blue_1 blue_9)
		(on blue_6 blue_1)
		(on blue_7 blue_6)
		(on red_7 blue_7)
		(clear red_7)

		(ontable green_1)
		(on yellow_4 green_1)
		(on red_2 yellow_4)
		(on red_3 red_2)
		(on yellow_14 red_3)
		(on blue_15 yellow_14)
		(on purple_8 blue_15)
		(on orange_15 purple_8)
		(clear orange_15)

		(ontable orange_9)
		(on blue_8 orange_9)
		(on blue_2 blue_8)
		(on blue_5 blue_2)
		(on blue_12 blue_5)
		(on yellow_2 blue_12)
		(on orange_1 yellow_2)
		(on red_14 orange_1)
		(clear red_14)

		(ontable green_12)
		(on green_8 green_12)
		(on orange_4 green_8)
		(on purple_4 orange_4)
		(on orange_6 purple_4)
		(on yellow_6 orange_6)
		(on yellow_3 yellow_6)
		(on purple_1 yellow_3)
		(on purple_5 purple_1)
		(clear purple_5)

		(ontable orange_14)
		(on green_7 orange_14)
		(on yellow_5 green_7)
		(on green_5 yellow_5)
		(on red_15 green_5)
		(on red_4 red_15)
		(on yellow_13 red_4)
		(on blue_13 yellow_13)
		(on purple_11 blue_13)
		(clear purple_11)
	)
	(:goal (and (handempty robot)
		(ontable red_3)
		(on blue_1 red_3)
		(on blue_6 blue_1)
		(on red_9 blue_6)
		(on orange_11 red_9)
		(on green_7 orange_11)
		(on blue_3 green_7)
		(on yellow_13 blue_3)
		(on blue_10 yellow_13)
		(clear blue_10)

		(ontable yellow_9)
		(on blue_13 yellow_9)
		(on purple_14 blue_13)
		(on orange_3 purple_14)
		(on blue_7 orange_3)
		(on orange_17 blue_7)
		(on yellow_1 orange_17)
		(on green_12 yellow_1)
		(on green_4 green_12)
		(clear green_4)

		(ontable orange_14)
		(on yellow_10 orange_14)
		(on red_8 yellow_10)
		(on blue_16 red_8)
		(on green_11 blue_16)
		(on green_2 green_11)
		(on yellow_5 green_2)
		(on yellow_14 yellow_5)
		(clear yellow_14)

		(ontable yellow_16)
		(on red_12 yellow_16)
		(on red_5 red_12)
		(on orange_8 red_5)
		(on yellow_6 orange_8)
		(on green_1 yellow_6)
		(on yellow_12 green_1)
		(on purple_9 yellow_12)
		(clear purple_9)

		(ontable purple_15)
		(on red_10 purple_15)
		(on red_1 red_10)
		(on red_13 red_1)
		(on purple_6 red_13)
		(on orange_1 purple_6)
		(on orange_2 orange_1)
		(on red_6 orange_2)
		(clear red_6)

		(ontable yellow_7)
		(on green_10 yellow_7)
		(on green_14 green_10)
		(on orange_7 green_14)
		(on purple_8 orange_7)
		(on green_6 purple_8)
		(on green_8 green_6)
		(on red_16 green_8)
		(clear red_16)

		(ontable yellow_15)
		(on blue_9 yellow_15)
		(on blue_15 blue_9)
		(on purple_12 blue_15)
		(on yellow_11 purple_12)
		(on orange_4 yellow_11)
		(on purple_2 orange_4)
		(on blue_8 purple_2)
		(clear blue_8)

		(ontable blue_14)
		(on blue_12 blue_14)
		(on blue_5 blue_12)
		(on blue_4 blue_5)
		(on yellow_17 blue_4)
		(on yellow_4 yellow_17)
		(on red_4 yellow_4)
		(on purple_11 red_4)
		(clear purple_11)

		(ontable green_17)
		(on red_14 green_17)
		(on purple_3 red_14)
		(on red_15 purple_3)
		(on red_11 red_15)
		(on blue_11 red_11)
		(on purple_4 blue_11)
		(on orange_13 purple_4)
		(clear orange_13)

		(ontable yellow_3)
		(on purple_1 yellow_3)
		(on purple_13 purple_1)
		(on green_13 purple_13)
		(on orange_6 green_13)
		(on purple_7 orange_6)
		(on green_9 purple_7)
		(on orange_12 green_9)
		(clear orange_12)

		(ontable purple_16)
		(on green_5 purple_16)
		(on purple_10 green_5)
		(on green_3 purple_10)
		(on yellow_8 green_3)
		(on blue_2 yellow_8)
		(on blue_17 blue_2)
		(on red_7 blue_17)
		(on green_15 red_7)
		(clear green_15)

		(ontable orange_16)
		(on orange_15 orange_16)
		(on purple_5 orange_15)
		(on green_16 purple_5)
		(on yellow_2 green_16)
		(on orange_5 yellow_2)
		(on orange_10 orange_5)
		(on red_2 orange_10)
		(on orange_9 red_2)
		(clear orange_9)
	))
)